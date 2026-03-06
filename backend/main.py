"""
로또 분석 API 서버 (FastAPI)
포트: 8010
"""
import csv
import io
import logging
import os
import sys
import uuid
import threading
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import settings
from database import (
    init_db, get_all_draws, get_draws_by_range, upsert_draw, get_latest_round,
    save_fixed_number, get_all_fixed_numbers, delete_fixed_number, update_fixed_number_memo,
    # 연금복권
    upsert_pension_draw, get_all_pension_draws, get_pension_draws_by_range,
    get_latest_pension_round, save_pension_weekly_recommend,
    get_pension_pending_result_rounds, update_pension_weekly_result,
    # 주간 추천 히스토리
    get_weekly_recommend,
)
from collector import fetch_draw, fetch_latest_round, collect_range, parse_csv_row, parse_xlsx
from pension_collector import (
    fetch_all_pension, fetch_new_pension_draws, fetch_latest_pension_round,
    parse_pension_xlsx, parse_pension_csv_row,
)
from pension_analysis import (
    get_full_pension_stats, simulate_pension_random, check_pension_rank,
)
from pension_recommender import (
    recommend_all_pension, weekly_pension_pick, recommend_by_digit_frequency,
    recommend_balanced as pension_recommend_balanced, recommend_random as pension_recommend_random,
)
from analysis.stats import get_full_stats, frequency_analysis, trend_analysis
from analysis.simulation import simulate_random, simulate_strategy, monte_carlo
from analysis.backtest import (
    run_backtest, run_cumulative_backtest,
    generate_recommendations, generate_fixed_number,
    run_real_sim, run_pattern_analysis, generate_pattern_recommend,
    run_pattern_sim, weekly_pick,
    METHODS, CONDITION_LABELS,
)
from recommender.engine import recommend_all, recommend_by_frequency, recommend_by_trend, recommend_balanced, recommend_random

# ── 비동기 작업 큐 (메모리) ──
_tasks: dict = {}   # task_id → {"status": "running"|"done"|"error", "result": ..., "error": ...}
_tasks_lock = threading.Lock()

def _run_task(task_id: str, fn, *args, **kwargs):
    try:
        result = fn(*args, **kwargs)
        with _tasks_lock:
            _tasks[task_id] = {"status": "done", "result": result}
    except Exception as e:
        with _tasks_lock:
            _tasks[task_id] = {"status": "error", "error": str(e)}

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


class BacktestRequest(BaseModel):
    window: int = 600                          # 학습 윈도우 (기존 분석: 600)
    methods: Optional[list[str]] = None        # None = 5개 전체
    sample_every: int = 10                     # 누적 차트 샘플링 간격


class BacktestRecommendRequest(BaseModel):
    method: str = "WEIGHTED_RECENT"            # 예측 방법
    window: int = 600                          # 학습 윈도우
    n_games: int = 20                          # 추천 번호 수
    condition_weights: Optional[dict] = None   # 조건별 가중치 (None = 균등)


class SaveFixedNumberRequest(BaseModel):
    numbers: list[int]
    score: Optional[float] = None
    rationale: Optional[dict] = None
    memo: str = ""


class UpdateMemoRequest(BaseModel):
    memo: str


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


@app.post("/api/collect/upload-xlsx")
async def upload_xlsx(file: UploadFile = File(...)):
    """
    동행복권 공식 엑셀 파일(.xlsx) 업로드로 일괄 등록
    컬럼: No | 회차 | 번호1~6 | 보너스 | 순위 | 당첨게임수 | 1게임당 당첨금액
    """
    if not file.filename or not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="xlsx 파일만 업로드 가능합니다")

    content = await file.read()
    try:
        data_list = parse_xlsx(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"엑셀 파싱 실패: {e}")

    success, fail = 0, 0
    for d in data_list:
        try:
            upsert_draw(d)
            success += 1
        except Exception as e:
            logger.warning(f"[upload_xlsx] upsert 실패: {e}")
            fail += 1

    return {
        "status": "ok",
        "filename": file.filename,
        "success": success,
        "fail": fail,
    }


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


# ───────────────────────────────────── 백테스팅 ──
@app.get("/api/backtest/methods")
def backtest_methods():
    """사용 가능한 예측 방법 + 조건 목록"""
    return {
        "methods": METHODS,
        "conditions": [
            {"key": k, "label": v} for k, v in CONDITION_LABELS.items()
        ],
    }


@app.post("/api/backtest/run")
def backtest_run(req: BacktestRequest):
    """
    슬라이딩 윈도우 백테스팅
    - 12개 조건 × 5가지 예측방법 정확도 측정
    - window 회차 학습 → 이후 회차 예측 vs 실제 비교
    - 주의: window=600이면 수십 초 소요
    """
    draws = get_all_draws()
    if len(draws) < req.window + 5:
        raise HTTPException(status_code=400, detail=f"데이터 부족 (현재 {len(draws)}회, 최소 {req.window + 5}회 필요)")
    if req.methods:
        invalid = [m for m in req.methods if m not in METHODS]
        if invalid:
            raise HTTPException(status_code=400, detail=f"알 수 없는 방법: {invalid}")
    result = run_backtest(draws, window=req.window, methods=req.methods)
    return {
        "total_tested":           result["total_tested"],
        "window":                 result["window"],
        "best_method":            result["best_method"],
        "ranking":                result["ranking"],
        "condition_accuracy_avg": result["condition_accuracy_avg"],
        "condition_labels":       result["condition_labels"],
        "methods": {
            m: {
                "avg_accuracy":       v["avg_accuracy"],
                "condition_accuracy": v["condition_accuracy"],
            }
            for m, v in result["methods"].items()
        },
    }


@app.post("/api/backtest/cumulative")
def backtest_cumulative(req: BacktestRequest):
    """누적 정확도 추이 (차트용)"""
    draws = get_all_draws()
    if len(draws) < req.window + 5:
        raise HTTPException(status_code=400, detail="데이터 부족")
    return run_cumulative_backtest(
        draws,
        window=req.window,
        methods=req.methods,
        sample_every=req.sample_every,
    )


@app.post("/api/backtest/recommend")
def backtest_recommend(req: BacktestRecommendRequest):
    """
    백테스팅 기반 번호 추천
    - window 회차 학습 → 다음 회차 조건 예측
    - 예측 조건을 만족하는 n_games개 번호 조합 생성
    """
    if req.method not in METHODS:
        raise HTTPException(status_code=400, detail=f"알 수 없는 방법: {req.method} (사용 가능: {METHODS})")
    draws = get_all_draws()
    if len(draws) < req.window:
        raise HTTPException(status_code=400, detail=f"데이터 부족 (현재 {len(draws)}회, 최소 {req.window}회 필요)")
    return generate_recommendations(
        draws,
        method=req.method,
        window=req.window,
        n_games=req.n_games,
        condition_weights=req.condition_weights,
    )


@app.get("/api/fixed")
def fixed_list():
    """저장된 고정번호 전체 조회"""
    return {"fixed_numbers": get_all_fixed_numbers()}


@app.post("/api/fixed")
def fixed_save(req: SaveFixedNumberRequest):
    """고정번호 저장"""
    if len(req.numbers) != 6:
        raise HTTPException(status_code=400, detail="번호는 6개여야 합니다")
    if not all(1 <= n <= 45 for n in req.numbers):
        raise HTTPException(status_code=400, detail="번호는 1~45 사이여야 합니다")
    new_id = save_fixed_number({
        "numbers":   sorted(req.numbers),
        "score":     req.score,
        "rationale": req.rationale or {},
        "memo":      req.memo,
    })
    return {"status": "ok", "id": new_id}


@app.delete("/api/fixed/{fixed_id}")
def fixed_delete(fixed_id: int):
    """고정번호 삭제"""
    if not delete_fixed_number(fixed_id):
        raise HTTPException(status_code=404, detail="해당 고정번호를 찾을 수 없습니다")
    return {"status": "ok"}


@app.patch("/api/fixed/{fixed_id}/memo")
def fixed_update_memo(fixed_id: int, req: UpdateMemoRequest):
    """고정번호 메모 수정"""
    if not update_fixed_number_memo(fixed_id, req.memo):
        raise HTTPException(status_code=404, detail="해당 고정번호를 찾을 수 없습니다")
    return {"status": "ok"}


@app.get("/api/backtest/fixed")
def backtest_fixed():
    """
    매주 고정 구매할 번호 1조 발급
    - 역대 전체 회차에서 조건별 최빈값(=가장 자주 등장한 구조) 산출
    - 해당 구조를 가장 잘 만족하는 번호 1조 생성
    - 합계 중앙값 범위, AC값, 끝자리 분포 등 추가 필터 적용
    """
    draws = get_all_draws()
    if len(draws) < 50:
        raise HTTPException(status_code=400, detail="데이터 부족 (최소 50회 필요)")
    return generate_fixed_number(draws)


@app.post("/api/backtest/pattern-sim")
def backtest_pattern_sim(
    n_games: int = 9,
    sample_every: int = 1,
    condition_window: int = 300,
):
    """비동기 시뮬레이션 시작 — task_id 반환. GET /api/backtest/pattern-sim/{task_id} 로 폴링"""
    draws = get_all_draws()
    if len(draws) < 15:
        raise HTTPException(status_code=400, detail="데이터 부족 (최소 15회 필요)")
    if n_games < 1 or n_games > 20:
        raise HTTPException(status_code=400, detail="n_games는 1~20 범위")
    if sample_every < 1 or sample_every > 100:
        raise HTTPException(status_code=400, detail="sample_every는 1~100 범위")

    task_id = str(uuid.uuid4())
    with _tasks_lock:
        _tasks[task_id] = {"status": "running"}

    t = threading.Thread(
        target=_run_task,
        args=(task_id, run_pattern_sim, draws),
        kwargs={"n_games": n_games, "condition_window": condition_window, "sample_every": sample_every},
        daemon=True,
    )
    t.start()
    return {"task_id": task_id, "status": "running"}


@app.get("/api/backtest/pattern-sim/{task_id}")
def backtest_pattern_sim_result(task_id: str):
    """비동기 시뮬레이션 결과 폴링"""
    with _tasks_lock:
        task = _tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task_id를 찾을 수 없습니다")
    if task["status"] == "running":
        return {"status": "running"}
    if task["status"] == "error":
        raise HTTPException(status_code=500, detail=task["error"])
    return {"status": "done", **task["result"]}


@app.post("/api/backtest/pattern-recommend")
def backtest_pattern_recommend(n_games: int = 9):
    """
    패턴 기반 번호 추천
    - 최근 회차 합계 방향/극단값 신호를 감지해 합계 타겟 범위를 좁힘
    - 유의한 신호: 합계 2연속 방향(p<0.0001), 극단 합계 회귀(p=0.0123)
    - 해당 합계 범위를 만족하는 n_games개 번호 조합 생성
    """
    draws = get_all_draws()
    if len(draws) < 10:
        raise HTTPException(status_code=400, detail="데이터 부족 (최소 10회 필요)")
    if n_games < 1 or n_games > 50:
        raise HTTPException(status_code=400, detail="n_games는 1~50 범위여야 합니다")
    return generate_pattern_recommend(draws, n_games=n_games)


@app.post("/api/backtest/weekly-pick")
def backtest_weekly_pick():
    """
    이번 주 추천 10게임 통합 반환

    구성:
      1. 고정번호 1조    — 역대 조건 최빈값 기반
      2. 조건 기반 4조   — WEIGHTED_RECENT 예측 조건 기반
      3. 패턴 기반 5조   — 합계 방향 신호 기반

    추가 인사이트:
      - 역대 4등 이상 당첨 유사 회차의 실제 번호 조건 역추적 분석
      - 공통 조건 최빈값 표시 (번호 생성 참고용)

    주의: 내부적으로 경량 시뮬레이션 실행 → 수십 초 소요 가능
    비동기 필요시 task_id 방식으로 전환 고려
    """
    draws = get_all_draws()
    if len(draws) < 15:
        raise HTTPException(status_code=400, detail="데이터 부족 (최소 15회 필요)")
    try:
        return weekly_pick(draws)
    except Exception as e:
        logger.error(f"[weekly_pick] 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/backtest/pattern-analysis")
def backtest_pattern_analysis():
    """
    신규 조건 6개 + 기존 핵심 조건의 실증 패턴 분석
    - 합계 방향 반전, 극단 합계 회귀, 2회 전 번호 재등장 등
    - 이론값 대비 실제 이탈 여부를 측정해 반환
    """
    draws = get_all_draws()
    if len(draws) < 100:
        raise HTTPException(status_code=400, detail="데이터 부족 (최소 100회 필요)")
    return run_pattern_analysis(draws)


@app.post("/api/backtest/real-sim")
def backtest_real_sim(
    method: str = "WEIGHTED_RECENT",
    window: int = 600,
    n_games: int = 9,
    sample_every: int = 10,
):
    """
    실전 당첨 시뮬레이션
    - 학습 윈도우 이후 각 회차마다 추천번호 생성 → 실제 당첨번호와 대조
    - 랜덤 구매와 ROI/당첨 빈도 비교
    """
    draws = get_all_draws()
    if len(draws) <= window:
        raise HTTPException(status_code=400, detail=f"데이터 부족 (최소 {window+1}회 필요)")
    try:
        return run_real_sim(draws, method=method, window=window,
                            n_games=n_games, sample_every=sample_every)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ───────────────────────────────────── 주간 추천 히스토리 ──
@app.get("/api/weekly-history")
def weekly_history(limit: int = 20):
    """
    주간 추천번호 히스토리 (최신순)
    - 이번 주 추천 + 과거 추천/결과 목록 반환
    - tbl_weekly_recommend 전체 조회 → 최신 limit개
    """
    import sqlite3, json as _json
    from config import settings as _s
    import os as _os

    _os.makedirs(_os.path.dirname(_s.DB_PATH), exist_ok=True)
    conn = sqlite3.connect(_s.DB_PATH)
    conn.row_factory = sqlite3.Row
    # source_labels 컬럼 없을 수 있으므로 마이그레이션
    try:
        conn.execute("ALTER TABLE tbl_weekly_recommend ADD COLUMN source_labels TEXT")
        conn.commit()
    except Exception:
        pass

    rows = conn.execute(
        "SELECT * FROM tbl_weekly_recommend ORDER BY target_round DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()

    history = []
    for row in rows:
        d = dict(row)
        try:
            d["games"]  = _json.loads(d["games"])  if d.get("games")  else []
        except Exception:
            d["games"] = []
        try:
            d["scores"] = _json.loads(d["scores"]) if d.get("scores") else []
        except Exception:
            d["scores"] = []
        try:
            d["fixed"]  = _json.loads(d["fixed"])  if d.get("fixed")  else []
        except Exception:
            d["fixed"] = []
        try:
            d["source_labels"] = _json.loads(d["source_labels"]) if d.get("source_labels") else []
        except Exception:
            d["source_labels"] = []
        if d.get("actual_numbers"):
            try:
                d["actual_numbers"] = _json.loads(d["actual_numbers"])
            except Exception:
                pass
        if d.get("result_detail"):
            try:
                d["result_detail"] = _json.loads(d["result_detail"])
            except Exception:
                pass
        history.append(d)
    return {"history": history, "total": len(history)}


# ───────────────────────────────────── 연금복권 ──

class PensionSimRequest(BaseModel):
    games_per_round: int = 5

class PensionRecommendRequest(BaseModel):
    strategy: str = "all"   # all | frequency | balanced | random
    games: int = 5


@app.get("/api/pension/status")
def pension_status():
    """연금복권 DB 현황"""
    draws = get_all_pension_draws()
    latest = draws[-1] if draws else None
    return {
        "total_rounds": len(draws),
        "latest_round": latest["round"] if latest else None,
        "latest_date":  latest["draw_date"] if latest else None,
    }


@app.post("/api/pension/collect/latest")
async def pension_collect_latest(background_tasks: BackgroundTasks):
    """최신 연금복권 회차 자동 수집 (백그라운드)"""
    db_latest = get_latest_pension_round()

    def _collect():
        new_draws = fetch_new_pension_draws(db_latest)
        for d in new_draws:
            upsert_pension_draw(d)
        logger.info(f"[pension_collect] {len(new_draws)}회차 저장 완료")

    background_tasks.add_task(_collect)
    return {
        "status": "started",
        "db_latest_round": db_latest,
        "message": "백그라운드에서 연금복권 데이터 수집 중입니다",
    }


@app.post("/api/pension/collect/all")
async def pension_collect_all(background_tasks: BackgroundTasks):
    """연금복권 전체 회차 수집 (백그라운드)"""
    def _collect():
        all_draws = fetch_all_pension()
        for d in all_draws:
            upsert_pension_draw(d)
        logger.info(f"[pension_collect_all] {len(all_draws)}회차 저장 완료")

    background_tasks.add_task(_collect)
    return {"status": "started", "message": "전체 연금복권 데이터 수집 시작"}


@app.post("/api/pension/collect/upload-xlsx")
async def pension_upload_xlsx(file: UploadFile = File(...)):
    """연금복권 엑셀 업로드"""
    if not file.filename or not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="xlsx 파일만 업로드 가능합니다")
    content = await file.read()
    try:
        data_list = parse_pension_xlsx(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"엑셀 파싱 실패: {e}")
    success, fail = 0, 0
    for d in data_list:
        try:
            upsert_pension_draw(d)
            success += 1
        except Exception as e:
            logger.warning(f"[pension_upload_xlsx] upsert 실패: {e}")
            fail += 1
    return {"status": "ok", "filename": file.filename, "success": success, "fail": fail}


@app.get("/api/pension/draws")
def pension_draws(start: Optional[int] = None, end: Optional[int] = None):
    """연금복권 당첨번호 조회"""
    if start and end:
        draws = get_pension_draws_by_range(start, end)
    else:
        draws = get_all_pension_draws()
    return {"total": len(draws), "draws": draws}


@app.get("/api/pension/draws/latest")
def pension_draws_latest():
    """연금복권 최신 5회차"""
    draws = get_all_pension_draws()
    return {"draws": draws[-5:] if draws else []}


@app.get("/api/pension/stats")
def pension_stats():
    """연금복권 전체 통계"""
    draws = get_all_pension_draws()
    if not draws:
        raise HTTPException(status_code=404, detail="데이터 없음 — 먼저 연금복권 데이터를 수집하세요")
    return get_full_pension_stats(draws)


@app.post("/api/pension/recommend")
def pension_recommend(req: PensionRecommendRequest):
    """연금복권 번호 추천"""
    valid = {"all", "frequency", "balanced", "random"}
    if req.strategy not in valid:
        raise HTTPException(status_code=400, detail=f"strategy는 {valid} 중 하나")
    draws = get_all_pension_draws()
    if req.strategy == "all":
        return recommend_all_pension(draws, games=req.games)
    elif req.strategy == "frequency":
        return {"games": recommend_by_digit_frequency(draws, games=req.games), "strategy": "frequency"}
    elif req.strategy == "balanced":
        return {"games": pension_recommend_balanced(draws, games=req.games), "strategy": "balanced"}
    elif req.strategy == "random":
        return {"games": pension_recommend_random(games=req.games), "strategy": "random"}


@app.post("/api/pension/simulate/random")
def pension_simulate_random(req: PensionSimRequest):
    """연금복권 랜덤 구매 시뮬레이션"""
    if req.games_per_round < 1 or req.games_per_round > 50:
        raise HTTPException(status_code=400, detail="games_per_round는 1~50 범위")
    draws = get_all_pension_draws()
    if not draws:
        raise HTTPException(status_code=404, detail="데이터 없음")
    return simulate_pension_random(draws, games_per_round=req.games_per_round)


@app.get("/api/pension/weekly-history")
def pension_weekly_history(limit: int = 20):
    """연금복권 주간 추천 히스토리"""
    import sqlite3, json as _json
    from config import settings as _s
    import os as _os
    _os.makedirs(_os.path.dirname(_s.DB_PATH), exist_ok=True)
    conn = sqlite3.connect(_s.DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM tbl_pension_weekly_recommend ORDER BY target_round DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    history = []
    for row in rows:
        d = dict(row)
        try:
            d["games"] = _json.loads(d["games"]) if d.get("games") else []
        except Exception:
            d["games"] = []
        if d.get("result_detail"):
            try:
                d["result_detail"] = _json.loads(d["result_detail"])
            except Exception:
                pass
        history.append(d)
    return {"history": history, "total": len(history)}


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
