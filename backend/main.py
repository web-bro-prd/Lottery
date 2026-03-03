"""
로또 분석 API 서버 (FastAPI)
포트: 8010
"""
import csv
import io
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import settings
from database import init_db, get_all_draws, get_draws_by_range, upsert_draw, get_latest_round
from collector import fetch_draw, fetch_latest_round, collect_range, parse_csv_row
from analysis.stats import get_full_stats, frequency_analysis, trend_analysis
from analysis.simulation import simulate_random, simulate_strategy, monte_carlo
from recommender.engine import recommend_all, recommend_by_frequency, recommend_by_trend, recommend_balanced, recommend_random

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ───────────────────────────────────── Lifespan ──
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("서버 시작 — DB 초기화")
    init_db()
    yield
    logger.info("서버 종료")


app = FastAPI(
    title="로또 분석 API",
    description="동행복권 데이터 기반 로또 번호 통계 분석 및 추천",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ───────────────────────────────────── Pydantic Models ──
class SimulateRandomRequest(BaseModel):
    games_per_round: int = 5
    start_round: Optional[int] = None
    end_round: Optional[int] = None


class SimulateStrategyRequest(BaseModel):
    strategy_numbers: list[list[int]]
    start_round: Optional[int] = None
    end_round: Optional[int] = None


class MonteCarloRequest(BaseModel):
    games: int = 1000
    trials: int = 10


class RecommendRequest(BaseModel):
    strategy: str = "all"   # all | frequency | trend | balanced | random
    games: int = 5
    recent_n: int = 50


# ───────────────────────────────────── 기본 ──
@app.get("/")
def root():
    return {"status": "ok", "service": "Lottery Analysis API", "version": "1.0.0"}


# ───────────────────────────────────── 데이터 수집 ──
@app.post("/api/collect/latest")
async def collect_latest(background_tasks: BackgroundTasks):
    """
    최신 회차까지 DB에 없는 회차 자동 수집
    (백그라운드 실행)
    """
    db_latest = get_latest_round()

    def _collect():
        api_latest = fetch_latest_round()
        if api_latest <= db_latest:
            logger.info(f"[collect] 이미 최신 상태 ({db_latest}회)")
            return
        logger.info(f"[collect] {db_latest + 1} ~ {api_latest}회 수집 시작")
        data_list = collect_range(db_latest + 1, api_latest)
        for d in data_list:
            upsert_draw(d)
        logger.info(f"[collect] {len(data_list)}회차 수집 완료")

    background_tasks.add_task(_collect)
    return {
        "status": "started",
        "db_latest_round": db_latest,
        "message": "백그라운드에서 수집 중입니다",
    }


@app.post("/api/collect/round/{round_no}")
def collect_single(round_no: int):
    """단일 회차 수집"""
    data = fetch_draw(round_no)
    if not data:
        raise HTTPException(status_code=404, detail=f"{round_no}회 데이터를 가져올 수 없습니다")
    upsert_draw(data)
    return {"status": "ok", "data": data}


@app.post("/api/collect/range")
def collect_range_api(start: int, end: int, background_tasks: BackgroundTasks):
    """회차 범위 수집 (백그라운드)"""
    if start > end:
        raise HTTPException(status_code=400, detail="start는 end보다 작아야 합니다")
    if end - start > 500:
        raise HTTPException(status_code=400, detail="한 번에 최대 500회차까지 수집 가능합니다")

    def _collect():
        data_list = collect_range(start, end)
        for d in data_list:
            upsert_draw(d)
        logger.info(f"[collect_range] {len(data_list)}회차 수집 완료")

    background_tasks.add_task(_collect)
    return {"status": "started", "start": start, "end": end}


@app.post("/api/collect/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """
    CSV 파일 업로드로 일괄 등록
    예상 컬럼: 회차, 추첨일, 번호1~6, 보너스
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV 파일만 업로드 가능합니다")

    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    success, fail = 0, 0
    for row in reader:
        data = parse_csv_row(dict(row))
        if data:
            upsert_draw(data)
            success += 1
        else:
            fail += 1

    return {
        "status": "ok",
        "filename": file.filename,
        "success": success,
        "fail": fail,
    }


# ───────────────────────────────────── 당첨 번호 조회 ──
@app.get("/api/draws")
def get_draws(start: Optional[int] = None, end: Optional[int] = None):
    """전체 or 범위 회차 데이터 반환"""
    if start and end:
        draws = get_draws_by_range(start, end)
    else:
        draws = get_all_draws()
    return {"total": len(draws), "draws": draws}


@app.get("/api/draws/latest")
def get_latest():
    """최신 5회차 데이터"""
    draws = get_all_draws()
    return {"draws": draws[-5:] if draws else []}


@app.get("/api/draws/{round_no}")
def get_draw(round_no: int):
    """특정 회차 데이터"""
    draws = get_draws_by_range(round_no, round_no)
    if not draws:
        raise HTTPException(status_code=404, detail=f"{round_no}회 데이터 없음")
    return draws[0]


# ───────────────────────────────────── 통계 분석 ──
@app.get("/api/stats")
def stats_all(start: Optional[int] = None, end: Optional[int] = None):
    """전체 통계 (회차 범위 필터 가능)"""
    if start and end:
        draws = get_draws_by_range(start, end)
    else:
        draws = get_all_draws()

    if not draws:
        raise HTTPException(status_code=404, detail="데이터 없음 — 먼저 데이터를 수집하세요")

    return get_full_stats(draws)


@app.get("/api/stats/frequency")
def stats_frequency(start: Optional[int] = None, end: Optional[int] = None):
    """번호별 출현 빈도"""
    draws = get_draws_by_range(start, end) if (start and end) else get_all_draws()
    if not draws:
        raise HTTPException(status_code=404, detail="데이터 없음")
    return frequency_analysis(draws)


@app.get("/api/stats/trend")
def stats_trend(recent_n: int = 50):
    """최근 트렌드 (핫/콜드 번호)"""
    draws = get_all_draws()
    if not draws:
        raise HTTPException(status_code=404, detail="데이터 없음")
    return trend_analysis(draws, recent_n=recent_n)


# ───────────────────────────────────── 시뮬레이션 ──
@app.post("/api/simulate/random")
def sim_random(req: SimulateRandomRequest):
    """랜덤 구매 시뮬레이션"""
    draws = get_all_draws()
    if not draws:
        raise HTTPException(status_code=404, detail="데이터 없음")
    return simulate_random(
        draws,
        games_per_round=req.games_per_round,
        start_round=req.start_round,
        end_round=req.end_round,
    )


@app.post("/api/simulate/strategy")
def sim_strategy(req: SimulateStrategyRequest):
    """특정 번호 고정 시뮬레이션"""
    # 유효성 검사
    for combo in req.strategy_numbers:
        if len(combo) != 6:
            raise HTTPException(status_code=400, detail="각 게임은 6개 번호여야 합니다")
        if not all(1 <= n <= 45 for n in combo):
            raise HTTPException(status_code=400, detail="번호는 1~45 사이여야 합니다")
        if len(set(combo)) != 6:
            raise HTTPException(status_code=400, detail="중복 번호가 있습니다")

    draws = get_all_draws()
    if not draws:
        raise HTTPException(status_code=404, detail="데이터 없음")
    return simulate_strategy(
        draws,
        strategy_numbers=req.strategy_numbers,
        start_round=req.start_round,
        end_round=req.end_round,
    )


@app.post("/api/simulate/montecarlo")
def sim_montecarlo(req: MonteCarloRequest):
    """몬테카를로 시뮬레이션"""
    if req.games > 100_000:
        raise HTTPException(status_code=400, detail="games는 최대 100,000")
    if req.trials > 100:
        raise HTTPException(status_code=400, detail="trials는 최대 100")
    return monte_carlo(games=req.games, trials=req.trials)


# ───────────────────────────────────── 번호 추천 ──
@app.post("/api/recommend")
def recommend(req: RecommendRequest):
    """번호 추천"""
    valid_strategies = {"all", "frequency", "trend", "balanced", "random"}
    if req.strategy not in valid_strategies:
        raise HTTPException(status_code=400, detail=f"strategy는 {valid_strategies} 중 하나")

    draws = get_all_draws()

    if req.strategy == "all":
        return recommend_all(draws, games=req.games)
    elif req.strategy == "frequency":
        return recommend_by_frequency(draws, games=req.games)
    elif req.strategy == "trend":
        return recommend_by_trend(draws, games=req.games, recent_n=req.recent_n)
    elif req.strategy == "balanced":
        return recommend_balanced(draws, games=req.games)
    elif req.strategy == "random":
        return recommend_random(games=req.games)


# ───────────────────────────────────── 서버 상태 ──
@app.get("/api/status")
def server_status():
    """DB 통계 요약"""
    draws = get_all_draws()
    latest = draws[-1] if draws else None
    return {
        "total_rounds": len(draws),
        "latest_round": latest["round"] if latest else None,
        "latest_date": latest["draw_date"] if latest else None,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level="info",
    )
