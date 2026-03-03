#!/usr/bin/env python3
"""
로또 주간 자동 작업 스크립트
크론: 30 21 * * 6  (매주 토요일 21:30)

흐름:
  1. 최신 당첨번호 DB 갱신
  2. 지난주 추천번호 결과 확인 → 결과 채널에 전송
  3. 다음 회차 고정번호 1개 + 추천번호 9게임 생성
  4. DB 저장
  5. 추천 채널에 전송
"""
import sys
import os
import logging

# 백엔드 디렉토리를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

from database import (
    init_db, get_latest_round, get_all_draws,
    save_weekly_recommend, get_pending_result_rounds, update_weekly_result,
    get_all_fixed_numbers,
)
from collector import fetch_latest_round, collect_range
from database import upsert_draw
from analysis.backtest import generate_recommendations, generate_fixed_number
from notify import send_weekly_numbers, send_result, send_error


def step1_collect() -> int:
    """최신 당첨번호 갱신. 반환값: 현재 DB 최신 회차"""
    db_latest = get_latest_round()
    api_latest = fetch_latest_round()
    if api_latest > db_latest:
        logger.info(f"[STEP1] {db_latest+1}~{api_latest}회 수집 시작")
        data_list = collect_range(db_latest + 1, api_latest)
        for d in data_list:
            upsert_draw(d)
        logger.info(f"[STEP1] {len(data_list)}회차 저장 완료")
    else:
        logger.info(f"[STEP1] 이미 최신 상태 ({db_latest}회)")
    return get_latest_round()


def step2_send_results():
    """지난주 추천번호 결과 확인 후 전송"""
    pending = get_pending_result_rounds()
    if not pending:
        logger.info("[STEP2] 결과 전송 대상 없음")
        return

    draws = {d["round"]: d for d in get_all_draws()}

    for rec in pending:
        target = rec["target_round"]
        draw = draws.get(target)
        if not draw:
            logger.info(f"[STEP2] {target}회 당첨번호 아직 없음 — 건너뜀")
            continue

        actual = [draw["num1"], draw["num2"], draw["num3"],
                  draw["num4"], draw["num5"], draw["num6"]]
        actual_set = set(actual)
        bonus = draw["bonus"]

        def _rank(game):
            matched = len(set(game) & actual_set)
            bonus_hit = bonus in set(game)
            if matched == 6: return 1
            if matched == 5 and bonus_hit: return 2
            if matched == 5: return 3
            if matched == 4: return 4
            if matched == 3: return 5
            return 0

        result_detail = []
        # 고정번호
        fixed = rec["fixed"]
        result_detail.append({
            "game": fixed,
            "rank": _rank(fixed),
            "matched": len(set(fixed) & actual_set),
            "is_fixed": True,
        })
        # 추천번호
        for game in rec["games"]:
            result_detail.append({
                "game": game,
                "rank": _rank(game),
                "matched": len(set(game) & actual_set),
                "is_fixed": False,
            })

        update_weekly_result(target, actual, bonus, result_detail)
        logger.info(f"[STEP2] {target}회 결과 저장 완료")

        send_result(
            target_round=target,
            actual_numbers=actual,
            actual_bonus=bonus,
            fixed_numbers=fixed,
            result_detail=result_detail,
        )
        logger.info(f"[STEP2] {target}회 결과 디스코드 전송 완료")


def step3_recommend_and_send(latest_round: int):
    """다음 회차 추천번호 생성 → 저장 → 전송"""
    next_round = latest_round + 1
    draws = get_all_draws()

    if not draws:
        logger.error("[STEP3] DB에 당첨번호 없음")
        return

    latest_draw = draws[-1]
    latest_numbers = [
        latest_draw["num1"], latest_draw["num2"], latest_draw["num3"],
        latest_draw["num4"], latest_draw["num5"], latest_draw["num6"],
    ]
    latest_bonus = latest_draw["bonus"]

    # 고정번호: DB에 저장된 것 중 가장 최근 것 사용, 없으면 자동 생성
    saved_fixed = get_all_fixed_numbers()
    if saved_fixed:
        fixed_numbers = saved_fixed[0]["numbers"]
        logger.info(f"[STEP3] 저장된 고정번호 사용: {fixed_numbers}")
    else:
        fixed_result = generate_fixed_number(draws)
        fixed_numbers = fixed_result["numbers"]
        logger.info(f"[STEP3] 고정번호 자동 생성: {fixed_numbers}")

    # 추천번호 9게임 (WEIGHTED_RECENT, window=600)
    rec = generate_recommendations(draws, method="WEIGHTED_RECENT", window=600, n_games=9)
    games  = rec["games"]
    scores = rec["scores"]
    logger.info(f"[STEP3] 추천번호 {len(games)}게임 생성 완료")

    # DB 저장
    save_weekly_recommend(next_round, games, scores, fixed_numbers)
    logger.info(f"[STEP3] {next_round}회 추천번호 DB 저장 완료")

    # 디스코드 전송
    ok = send_weekly_numbers(
        latest_round=latest_round,
        latest_numbers=latest_numbers,
        latest_bonus=latest_bonus,
        fixed_numbers=fixed_numbers,
        recommend_games=games,
        recommend_scores=scores,
        next_round=next_round,
    )
    if ok:
        logger.info(f"[STEP3] {next_round}회 추천번호 디스코드 전송 완료")
    else:
        logger.error(f"[STEP3] 디스코드 전송 실패")


def main():
    logger.info("===== 로또 주간 작업 시작 =====")
    try:
        init_db()
        latest_round = step1_collect()
        step2_send_results()
        step3_recommend_and_send(latest_round)
        logger.info("===== 로또 주간 작업 완료 =====")
    except Exception as e:
        logger.exception(f"주간 작업 오류: {e}")
        send_error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
