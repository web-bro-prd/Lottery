"""
백테스팅 엔진 — 번호 예측 기법들을 역대 회차 데이터로 검증

슬라이딩 윈도우 방식:
  - 직전 window 회차 데이터로 번호 예측
  - 다음 회차 실제 번호와 대조
  - 매칭 개수 → 등수 계산
  - 모든 기법의 결과를 회차별로 기록

기법 목록:
  1. frequency     최근 N회 최다 출현 번호 6개
  2. cold          최근 N회 최소 출현 번호 6개 (오랫동안 안 나온 번호)
  3. delta         번호 간 차이값(delta) 분포에서 역대 최빈 델타 패턴 재현
  4. zone_balance  구간(1-9, 10-19, 20-29, 30-39, 40-45) 역대 비율로 배분
  5. odd_even      역대 홀짝 비율 중심의 조합
  6. sum_center    역대 당첨번호 합계 중앙값에 가까운 조합
  7. no_consec     연속번호가 없는 조합 중 빈도 가중 선택
"""
import random
import logging
from collections import Counter
from typing import Callable

logger = logging.getLogger(__name__)

PRIZE_TABLE = {6: 2_000_000_000, 5: 55_000, 4: 5_000, 3: 1_000}  # 고정 근사값 (원)
TICKET_PRICE = 1_000


# ─────────────────────────────── helpers ───────────────────────────────

def _nums(draw: dict) -> list[int]:
    return [draw["num1"], draw["num2"], draw["num3"],
            draw["num4"], draw["num5"], draw["num6"]]


def _match_rank(predicted: list[int], actual_nums: list[int], bonus: int) -> int:
    """예측 번호 6개와 실제 당첨 번호 비교 → 등수 반환 (0 = 미당첨)"""
    matched = len(set(predicted) & set(actual_nums))
    if matched == 6:
        return 1
    if matched == 5 and bonus in predicted:
        return 2
    if matched == 5:
        return 3
    if matched == 4:
        return 4
    if matched == 3:
        return 5
    return 0


def _best_of(candidates: list[list[int]], actual_nums: list[int], bonus: int) -> int:
    """여러 게임 예측 중 가장 좋은 등수 반환"""
    best = 0
    for cand in candidates:
        r = _match_rank(cand, actual_nums, bonus)
        if r == 0:
            continue
        if best == 0 or r < best:
            best = r
    return best


# ─────────────────────────────── 기법들 ────────────────────────────────

def _strategy_frequency(window: list[dict], games: int = 1) -> list[list[int]]:
    """최근 window에서 가장 많이 나온 번호 우선 선택"""
    cnt = Counter()
    for d in window:
        for n in _nums(d):
            cnt[n] += 1
    top = [n for n, _ in cnt.most_common()]
    # 상위 빈도 번호 풀에서 games개 조합 생성
    pool = top[:20] if len(top) >= 20 else top
    result = []
    for _ in range(games):
        pick = sorted(random.sample(pool, 6))
        result.append(pick)
    return result


def _strategy_cold(window: list[dict], games: int = 1) -> list[list[int]]:
    """최근 window에서 가장 적게 나온 번호 우선 선택"""
    cnt = Counter({n: 0 for n in range(1, 46)})
    for d in window:
        for n in _nums(d):
            cnt[n] += 1
    bottom = [n for n, _ in cnt.most_common()[::-1]]
    pool = bottom[:20]
    result = []
    for _ in range(games):
        pick = sorted(random.sample(pool, 6))
        result.append(pick)
    return result


def _strategy_delta(window: list[dict], games: int = 1) -> list[list[int]]:
    """
    역대 당첨번호의 delta(번호 간 차이) 분포에서
    가장 자주 나오는 delta 패턴으로 번호 생성
    """
    delta_counts = Counter()
    for d in window:
        nums = sorted(_nums(d))
        deltas = tuple(nums[i+1] - nums[i] for i in range(5))
        delta_counts[deltas] += 1

    # 상위 delta 패턴 중 하나 선택하여 번호 생성
    top_deltas = [d for d, _ in delta_counts.most_common(10)]

    result = []
    for _ in range(games):
        for attempt in range(50):
            pattern = random.choice(top_deltas) if top_deltas else (1, 2, 3, 4, 5)
            start = random.randint(1, 45 - sum(pattern))
            nums = [start]
            for delta in pattern:
                nums.append(nums[-1] + delta)
            if all(1 <= n <= 45 for n in nums) and len(set(nums)) == 6:
                result.append(sorted(nums))
                break
        else:
            result.append(sorted(random.sample(range(1, 46), 6)))
    return result


def _strategy_zone_balance(window: list[dict], games: int = 1) -> list[list[int]]:
    """
    구간(1-9, 10-19, 20-29, 30-39, 40-45) 역대 등장 비율로 배분
    """
    zones = [(1, 9), (10, 19), (20, 29), (30, 39), (40, 45)]
    zone_counts = [0] * 5

    for d in window:
        for n in _nums(d):
            for i, (lo, hi) in enumerate(zones):
                if lo <= n <= hi:
                    zone_counts[i] += 1

    total = sum(zone_counts) or 1
    # 각 구간 기대 개수 (반올림, 합 6개 맞추기)
    ratios = [c / total for c in zone_counts]
    counts = [round(r * 6) for r in ratios]
    # 합이 6이 안 되면 조정
    diff = 6 - sum(counts)
    if diff > 0:
        for i in sorted(range(5), key=lambda x: ratios[x], reverse=True)[:diff]:
            counts[i] += 1
    elif diff < 0:
        for i in sorted(range(5), key=lambda x: counts[x], reverse=True)[:-diff]:
            if counts[i] > 0:
                counts[i] -= 1

    result = []
    for _ in range(games):
        pick = []
        for i, (lo, hi) in enumerate(zones):
            n = counts[i]
            pool = list(range(lo, hi + 1))
            pick.extend(random.sample(pool, min(n, len(pool))))
        # 부족하면 전체 풀에서 보충
        remaining = [n for n in range(1, 46) if n not in pick]
        while len(pick) < 6:
            pick.append(random.choice(remaining))
            remaining = [n for n in remaining if n not in pick]
        result.append(sorted(pick[:6]))
    return result


def _strategy_odd_even(window: list[dict], games: int = 1) -> list[list[int]]:
    """역대 당첨번호 홀짝 비율 중심 조합"""
    odd_counts = []
    for d in window:
        odds = sum(1 for n in _nums(d) if n % 2 == 1)
        odd_counts.append(odds)

    # 가장 빈번한 홀수 개수
    target_odd = Counter(odd_counts).most_common(1)[0][0]
    target_even = 6 - target_odd

    odds_pool = list(range(1, 46, 2))   # 홀수
    evens_pool = list(range(2, 46, 2))  # 짝수

    result = []
    for _ in range(games):
        pick = random.sample(odds_pool, min(target_odd, len(odds_pool))) + \
               random.sample(evens_pool, min(target_even, len(evens_pool)))
        result.append(sorted(pick[:6]))
    return result


def _strategy_sum_center(window: list[dict], games: int = 1) -> list[list[int]]:
    """
    역대 당첨번호 합계의 중앙값 근처 번호 조합 생성
    (당첨번호 합계는 통상 100~175 범위에 밀집)
    """
    sums = [sum(_nums(d)) for d in window]
    target_sum = int(sorted(sums)[len(sums) // 2])  # 중앙값

    result = []
    for _ in range(games):
        for _ in range(200):
            pick = sorted(random.sample(range(1, 46), 6))
            if abs(sum(pick) - target_sum) <= 10:
                result.append(pick)
                break
        else:
            result.append(sorted(random.sample(range(1, 46), 6)))
    return result


def _strategy_no_consec(window: list[dict], games: int = 1) -> list[list[int]]:
    """
    연속번호 없는 조합 + 빈도 가중치 적용
    (연속번호 포함 비율이 낮다면 회피가 유리할 수 있음)
    """
    cnt = Counter()
    for d in window:
        for n in _nums(d):
            cnt[n] += 1

    # 빈도 기반 가중 풀 (상위 30개)
    pool = [n for n, _ in cnt.most_common(30)]

    result = []
    for _ in range(games):
        for _ in range(200):
            pick = sorted(random.sample(pool if len(pool) >= 6 else range(1, 46), 6))
            # 연속번호 없는지 확인
            has_consec = any(pick[i+1] - pick[i] == 1 for i in range(5))
            if not has_consec:
                result.append(pick)
                break
        else:
            result.append(sorted(random.sample(range(1, 46), 6)))
    return result


# ─────────────────────────────── 백테스팅 코어 ─────────────────────────

STRATEGIES: dict[str, Callable] = {
    "frequency":    _strategy_frequency,
    "cold":         _strategy_cold,
    "delta":        _strategy_delta,
    "zone_balance": _strategy_zone_balance,
    "odd_even":     _strategy_odd_even,
    "sum_center":   _strategy_sum_center,
    "no_consec":    _strategy_no_consec,
}

STRATEGY_LABELS = {
    "frequency":    "빈도 기반",
    "cold":         "콜드 번호",
    "delta":        "델타 패턴",
    "zone_balance": "구간 균형",
    "odd_even":     "홀짝 비율",
    "sum_center":   "합계 중심",
    "no_consec":    "연속 회피",
}


def run_backtest(
    draws: list[dict],
    window: int = 50,
    games_per_pick: int = 5,
    strategy_names: list[str] | None = None,
) -> dict:
    """
    슬라이딩 윈도우 백테스팅 실행

    Args:
        draws:           전체 회차 데이터 (오름차순 정렬)
        window:          학습에 사용할 직전 회차 수
        games_per_pick:  회차당 예측 게임 수
        strategy_names:  실행할 기법 목록 (None = 전체)

    Returns:
        {
          "window": 50,
          "games_per_pick": 5,
          "total_rounds": 1163,   # 백테스팅된 회차 수
          "strategies": {
            "frequency": {
              "label": "빈도 기반",
              "rank_counts": {0: 950, 3: 8, 4: 4, 5: 1},
              "hit_rounds": [{"round": 123, "rank": 3, ...}, ...],
              "roi": -45.2,
              "score": 12.3,      # 가중 점수
            },
            ...
          },
          "ranking": ["odd_even", "frequency", ...]   # 스코어 순
        }
    """
    if len(draws) < window + 1:
        return {"error": "데이터가 부족합니다"}

    draws_sorted = sorted(draws, key=lambda d: d["round"])
    target_strategies = strategy_names or list(STRATEGIES.keys())

    # 결과 초기화
    results: dict[str, dict] = {}
    for name in target_strategies:
        results[name] = {
            "label": STRATEGY_LABELS.get(name, name),
            "rank_counts": {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            "hit_rounds": [],
            "total_spent": 0,
            "total_prize": 0,
        }

    # 슬라이딩 윈도우 순회
    for i in range(window, len(draws_sorted)):
        test_draw = draws_sorted[i]
        train_window = draws_sorted[i - window: i]
        actual_nums = _nums(test_draw)
        bonus = test_draw["bonus"]

        for name in target_strategies:
            fn = STRATEGIES[name]
            predicted_games = fn(train_window, games=games_per_pick)
            best_rank = _best_of(predicted_games, actual_nums, bonus)

            results[name]["rank_counts"][best_rank] += 1
            results[name]["total_spent"] += TICKET_PRICE * games_per_pick

            if best_rank > 0:
                prize = PRIZE_TABLE.get(best_rank, 0)
                results[name]["total_prize"] += prize
                results[name]["hit_rounds"].append({
                    "round":    test_draw["round"],
                    "draw_date": test_draw.get("draw_date", ""),
                    "rank":     best_rank,
                    "actual":   actual_nums,
                    "bonus":    bonus,
                })

    # ROI, 스코어 계산
    # 스코어: 등수별 가중치 합 (1등=1000, 2등=100, 3등=10, 4등=3, 5등=1)
    WEIGHTS = {1: 1000, 2: 100, 3: 10, 4: 3, 5: 1}
    scored = []
    for name, r in results.items():
        spent = r["total_spent"]
        prize = r["total_prize"]
        roi = round((prize - spent) / spent * 100, 2) if spent > 0 else 0.0
        score = sum(WEIGHTS.get(rank, 0) * cnt
                    for rank, cnt in r["rank_counts"].items())
        r["roi"] = roi
        r["score"] = score
        r["hit_count"] = sum(cnt for rank, cnt in r["rank_counts"].items() if rank > 0)
        scored.append((name, score))

    ranking = [name for name, _ in sorted(scored, key=lambda x: x[1], reverse=True)]

    tested_count = len(draws_sorted) - window
    logger.info(f"[backtest] {tested_count}회차 × {len(target_strategies)}기법 완료")

    return {
        "window": window,
        "games_per_pick": games_per_pick,
        "total_rounds": tested_count,
        "strategies": results,
        "ranking": ranking,
    }


def run_cumulative_backtest(
    draws: list[dict],
    window: int = 50,
    games_per_pick: int = 5,
    strategy_names: list[str] | None = None,
    sample_every: int = 10,
) -> dict:
    """
    누적 성과 추이 계산 (차트용)
    sample_every 회차마다 누적 스코어를 기록

    Returns:
        {
          "rounds": [101, 111, 121, ...],
          "series": {
            "frequency": [0, 1, 1, 4, ...],   # 누적 스코어
            ...
          }
        }
    """
    draws_sorted = sorted(draws, key=lambda d: d["round"])
    target_strategies = strategy_names or list(STRATEGIES.keys())
    WEIGHTS = {1: 1000, 2: 100, 3: 10, 4: 3, 5: 1}

    cumulative = {name: 0 for name in target_strategies}
    rounds_axis = []
    series: dict[str, list[int]] = {name: [] for name in target_strategies}

    for i in range(window, len(draws_sorted)):
        test_draw = draws_sorted[i]
        train_window = draws_sorted[i - window: i]
        actual_nums = _nums(test_draw)
        bonus = test_draw["bonus"]

        for name in target_strategies:
            fn = STRATEGIES[name]
            predicted_games = fn(train_window, games=games_per_pick)
            best_rank = _best_of(predicted_games, actual_nums, bonus)
            cumulative[name] += WEIGHTS.get(best_rank, 0)

        if (i - window) % sample_every == 0:
            rounds_axis.append(test_draw["round"])
            for name in target_strategies:
                series[name].append(cumulative[name])

    return {
        "rounds": rounds_axis,
        "series": series,
        "labels": {name: STRATEGY_LABELS.get(name, name) for name in target_strategies},
    }
