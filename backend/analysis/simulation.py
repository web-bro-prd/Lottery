"""
로또 시뮬레이션 엔진

기능:
- 랜덤 구매 시뮬레이션 (N회 구매)
- 특정 전략 기반 구매 시뮬레이션
- 수익률 계산
"""
import random
from typing import Any


# 로또 당첨금 (근사값)
PRIZE_TABLE = {
    1: 2_000_000_000,   # 1등: 20억 (유동, 편의상 고정)
    2: 60_000_000,      # 2등: 6천만
    3: 1_500_000,       # 3등: 150만
    4: 50_000,          # 4등: 5만
    5: 5_000,           # 5등: 5천
}

TICKET_PRICE = 1_000    # 1게임 1천원


def check_rank(my_nums: set[int], winning_nums: set[int], bonus: int) -> int:
    """
    등수 반환 (0 = 미당첨)
    """
    match_count = len(my_nums & winning_nums)
    has_bonus = bonus in my_nums

    if match_count == 6:
        return 1
    elif match_count == 5 and has_bonus:
        return 2
    elif match_count == 5:
        return 3
    elif match_count == 4:
        return 4
    elif match_count == 3:
        return 5
    return 0


def simulate_random(
    draws: list[dict],
    games_per_round: int = 5,
    start_round: int = None,
    end_round: int = None,
) -> dict[str, Any]:
    """
    완전 랜덤 구매 시뮬레이션

    - 각 회차마다 games_per_round 게임씩 랜덤 구매
    - 실제 당첨 번호와 대조
    """
    if not draws:
        return {}

    # 회차 필터
    if start_round:
        draws = [d for d in draws if d["round"] >= start_round]
    if end_round:
        draws = [d for d in draws if d["round"] <= end_round]

    total_spent = 0
    total_prize = 0
    rank_counter = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 0: 0}
    results = []

    for draw in draws:
        winning = {draw["num1"], draw["num2"], draw["num3"], draw["num4"], draw["num5"], draw["num6"]}
        bonus = draw["bonus"]

        round_prize = 0
        round_ranks = []
        for _ in range(games_per_round):
            my_nums = set(random.sample(range(1, 46), 6))
            rank = check_rank(my_nums, winning, bonus)
            prize = PRIZE_TABLE.get(rank, 0)
            round_prize += prize
            round_ranks.append(rank)
            rank_counter[rank] += 1

        spent = games_per_round * TICKET_PRICE
        total_spent += spent
        total_prize += round_prize

        results.append({
            "round": draw["round"],
            "spent": spent,
            "prize": round_prize,
        })

    roi = round((total_prize - total_spent) / total_spent * 100, 2) if total_spent else 0

    return {
        "type": "random",
        "rounds_played": len(draws),
        "games_per_round": games_per_round,
        "total_spent": total_spent,
        "total_prize": total_prize,
        "net": total_prize - total_spent,
        "roi": roi,
        "rank_summary": rank_counter,
        "detail": results[-20:],   # 최근 20회차만 반환
    }


def simulate_strategy(
    draws: list[dict],
    strategy_numbers: list[list[int]],   # 고정 번호 세트 (최대 5게임)
    start_round: int = None,
    end_round: int = None,
) -> dict[str, Any]:
    """
    특정 번호 조합 고정 구매 시뮬레이션

    strategy_numbers: [[1,2,3,4,5,6], [7,8,9,10,11,12], ...]
    """
    if not draws or not strategy_numbers:
        return {}

    if start_round:
        draws = [d for d in draws if d["round"] >= start_round]
    if end_round:
        draws = [d for d in draws if d["round"] <= end_round]

    games_per_round = len(strategy_numbers)
    total_spent = 0
    total_prize = 0
    rank_counter = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 0: 0}
    results = []

    for draw in draws:
        winning = {draw["num1"], draw["num2"], draw["num3"], draw["num4"], draw["num5"], draw["num6"]}
        bonus = draw["bonus"]

        round_prize = 0
        for nums in strategy_numbers:
            rank = check_rank(set(nums), winning, bonus)
            prize = PRIZE_TABLE.get(rank, 0)
            round_prize += prize
            rank_counter[rank] += 1

        spent = games_per_round * TICKET_PRICE
        total_spent += spent
        total_prize += round_prize

        results.append({
            "round": draw["round"],
            "spent": spent,
            "prize": round_prize,
        })

    roi = round((total_prize - total_spent) / total_spent * 100, 2) if total_spent else 0

    return {
        "type": "strategy",
        "strategy_numbers": strategy_numbers,
        "rounds_played": len(draws),
        "games_per_round": games_per_round,
        "total_spent": total_spent,
        "total_prize": total_prize,
        "net": total_prize - total_spent,
        "roi": roi,
        "rank_summary": rank_counter,
        "detail": results[-20:],
    }


def monte_carlo(
    games: int = 1000,
    trials: int = 10,
) -> dict[str, Any]:
    """
    몬테카를로 시뮬레이션
    - trials회 반복하여 ROI 분포 계산
    """
    roi_list = []

    for _ in range(trials):
        spent = games * TICKET_PRICE
        prize = 0
        for _ in range(games):
            my_nums = set(random.sample(range(1, 46), 6))
            winning = set(random.sample(range(1, 46), 6))
            bonus = random.choice(list(set(range(1, 46)) - winning))
            rank = check_rank(my_nums, winning, bonus)
            prize += PRIZE_TABLE.get(rank, 0)
        roi_list.append(round((prize - spent) / spent * 100, 4))

    return {
        "games": games,
        "trials": trials,
        "avg_roi": round(sum(roi_list) / len(roi_list), 4) if roi_list else 0,
        "min_roi": min(roi_list) if roi_list else 0,
        "max_roi": max(roi_list) if roi_list else 0,
        "roi_distribution": roi_list,
    }
