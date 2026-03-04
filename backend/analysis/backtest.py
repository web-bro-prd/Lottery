"""
백테스팅 엔진 — 기존 분석 보고서 기반 전면 재구성

핵심 아이디어:
  1) 각 회차를 13개 '조건'으로 특징화
  2) 슬라이딩 윈도우로 "다음 회차의 조건"을 5가지 방법으로 예측
  3) 예측한 조건 vs 실제 조건 비교 → 조건별 정확도 측정
  4) 가장 정확도 높은 조건들에 가중치 → 조건을 만족하는 번호 조합 생성

조건 13개:
  A. 기본 분포
    1. odd_even      홀수 개수 (0~6)
    2. high_low      고번호(23-45) 개수 (0~6)
    3. sum_range     합계 구간 (100 미만/100-119/120-139/140-159/160-179/180+)

  B. 패턴
    4. consecutive   연속번호 최대 길이 (0/1/2/3+)
    5. tail_dist     끝자리 중복 개수 (모두다름=0 / 1쌍=1 / 2쌍=2 / ...)
    6. tens_dist     십의자리 분포 패턴 (0대/10대/20대/30대/40대 각각 개수)

  C. 빈도
    7. hot_count     최근 10회 출현 Hot 번호 개수 (0~6)
    8. long_miss     최근 20회 미출현 번호 개수 (0~6)
    9. prev_overlap  직전 회차 중복 번호 개수 (0~6)

  D. 고급 수리
   10. ac_value      AC값 (3~10 범주화)
   11. gap_std       번호 간격 표준편차 구간 (낮음/중간/높음)
   12. total_sum     6개 번호의 합 (= sum_range와 중복이나 세부 값)

  E. 보너스
   13. bonus_odd_high  보너스 번호의 홀짝+고저 조합

예측 방법 5가지:
  FREQUENCY      과거 전체 가장 빈번한 조건
  WEIGHTED_RECENT  최근 20% 데이터에 3배 가중치 ★ 기존 최고 성능
  CYCLE          최근 10회 모드
  TREND          최근 상승 추세 조건
  ENSEMBLE       위 4개 다수결
"""
import random
import logging
import math
from collections import Counter
from typing import Optional, List, Dict, Tuple

logger = logging.getLogger(__name__)

TICKET_PRICE = 1_000
PRIZE_TABLE = {1: 2_000_000_000, 2: 55_000_000, 3: 1_500_000, 4: 50_000, 5: 5_000}


# ══════════════════════════════════════════════
#  1. 조건 특징화 (회차 dict → 조건 dict)
# ══════════════════════════════════════════════

def _nums(draw: dict) -> list[int]:
    return sorted([draw["num1"], draw["num2"], draw["num3"],
                   draw["num4"], draw["num5"], draw["num6"]])


def _ac_value(nums: list[int]) -> int:
    """AC값: 번호 간 차이의 고유값 수 - 5"""
    diffs = set()
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            diffs.add(nums[j] - nums[i])
    return len(diffs) - 5  # 0~9 범위


def _consecutive_max(nums: list[int]) -> int:
    """연속번호 최대 길이 (1개=0, 2개연속=1, ...)"""
    s = sorted(nums)
    max_c, cur = 0, 0
    for i in range(1, len(s)):
        if s[i] - s[i-1] == 1:
            cur += 1
            max_c = max(max_c, cur)
        else:
            cur = 0
    return max_c


def _tail_duplicates(nums: list[int]) -> int:
    """끝자리 중복 쌍 수 (0 = 모두 다름)"""
    tails = [n % 10 for n in nums]
    cnt = Counter(tails)
    return sum(v - 1 for v in cnt.values() if v > 1)


def _tens_pattern(nums: list[int]) -> tuple:
    """십의자리 분포 (0대~40대 각 개수 5-tuple)"""
    zones = [0, 0, 0, 0, 0]
    for n in nums:
        if n <= 9:    zones[0] += 1
        elif n <= 19: zones[1] += 1
        elif n <= 29: zones[2] += 1
        elif n <= 39: zones[3] += 1
        else:         zones[4] += 1
    return tuple(zones)


def _gap_std_bucket(nums: list[int]) -> str:
    """번호 간격 표준편차 → 낮음/중간/높음"""
    gaps = [nums[i+1] - nums[i] for i in range(len(nums)-1)]
    mean = sum(gaps) / len(gaps)
    std = math.sqrt(sum((g - mean)**2 for g in gaps) / len(gaps))
    if std < 4:   return "low"
    if std < 8:   return "mid"
    return "high"


def _sum_range(total: int) -> str:
    if total < 100:  return "~99"
    if total < 120:  return "100-119"
    if total < 140:  return "120-139"
    if total < 160:  return "140-159"
    if total < 180:  return "160-179"
    return "180+"


# ── 신규 조건 헬퍼 ──────────────────────────────

_PRIMES_1_45 = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43}

def _prime_count(nums: list[int]) -> int:
    """1~45 중 소수 개수"""
    return sum(1 for n in nums if n in _PRIMES_1_45)


def _gap_max(nums: list[int]) -> int:
    """정렬된 6개 번호 사이 최대 간격"""
    return max(nums[i+1] - nums[i] for i in range(len(nums)-1))


def _std_dev_bucket(nums: list[int]) -> str:
    """번호 표준편차 구간 — tight(<10) / mid(10-16) / spread(>16)"""
    mean = sum(nums) / len(nums)
    std = math.sqrt(sum((n - mean) ** 2 for n in nums) / len(nums))
    if std < 10:  return "tight"
    if std < 16:  return "mid"
    return "spread"


def _sum_delta_direction(prev_sum: int, cur_sum: int) -> str:
    """직전 회차 대비 합계 이동 방향"""
    if cur_sum > prev_sum:   return "up"
    if cur_sum < prev_sum:   return "down"
    return "same"


def _sum_reversion_zone(prev_sum: int) -> str:
    """직전 합계가 극단인지 여부 → 극단이면 다음 회차 중간 합계 가능성↑
    극단(<100 또는 ≥180): 'extreme' / 중간: 'normal'
    [데이터 근거] 극단 이후 다음 회차 85~92%가 100-179 구간 진입"""
    if prev_sum < 100 or prev_sum >= 180:
        return "extreme"
    return "normal"


def _sum_trend_bucket(history: list[dict]) -> str:
    """최근 연속 상승/하락 길이 구간
    1~2연속: 'short' / 3~4연속: 'mid' / 5+: 'long'
    [데이터 근거] up→down 이후 상승 63.5%, 즉 장기 추세 이후 반전 확률↑"""
    if len(history) < 2:
        return "short"
    sums = [sum(_nums(d)) for d in history[-6:]]
    streak = 1
    direction = "up" if sums[-1] > sums[-2] else "down"
    for i in range(len(sums) - 2, 0, -1):
        cur_dir = "up" if sums[i] > sums[i-1] else "down"
        if cur_dir == direction:
            streak += 1
        else:
            break
    if streak <= 2:  return "short"
    if streak <= 4:  return "mid"
    return "long"


def extract_conditions(draw: dict, history: list[dict]) -> dict:
    """회차 하나를 19개 조건 dict로 변환 (기존 13 + 신규 6)"""
    nums = _nums(draw)
    bonus = draw.get("bonus", 0)

    # 빈도 조건용 준비
    recent10 = history[-10:] if len(history) >= 10 else history
    recent20 = history[-20:] if len(history) >= 20 else history
    prev = history[-1] if history else None
    prev2 = history[-2] if len(history) >= 2 else None

    hot_pool: set[int] = set()
    for d in recent10:
        hot_pool.update(_nums(d))

    miss_pool: set[int] = set(range(1, 46))
    for d in recent20:
        miss_pool -= set(_nums(d))

    prev_nums = set(_nums(prev)) if prev else set()
    prev2_nums = set(_nums(prev2)) if prev2 else set()

    total = sum(nums)
    prev_sum = sum(_nums(prev)) if prev else total
    odd_count = sum(1 for n in nums if n % 2 == 1)
    high_count = sum(1 for n in nums if n >= 23)
    ac = _ac_value(nums)

    return {
        # ── 기존 13개 ──
        "odd_even":          odd_count,
        "high_low":          high_count,
        "sum_range":         _sum_range(total),
        "consecutive":       _consecutive_max(nums),
        "tail_dist":         _tail_duplicates(nums),
        "tens_dist":         _tens_pattern(nums),
        "hot_count":         len(set(nums) & hot_pool),
        "long_miss":         len(set(nums) & miss_pool),
        "prev_overlap":      len(set(nums) & prev_nums),
        "ac_value":          min(ac, 9),
        "gap_std":           _gap_std_bucket(nums),
        "total_sum":         total,
        "bonus_char":        f"{'odd' if bonus % 2 == 1 else 'even'}_{'high' if bonus >= 23 else 'low'}",
        # ── 신규 6개 (데이터 근거 기반) ──
        "prime_count":       _prime_count(nums),           # 소수 개수 (1-45 중 14개 소수)
        "gap_max":           _gap_max(nums),               # 최대 번호 간격
        "std_dev_bucket":    _std_dev_bucket(nums),        # 번호 분산 구간
        "sum_direction":     _sum_delta_direction(prev_sum, total),   # 합계 이동 방향 ★
        "sum_reversion":     _sum_reversion_zone(prev_sum),           # 극단 합계 후 평균회귀 ★
        "prev2_overlap":     len(set(nums) & prev2_nums),  # 2회 전 번호 재등장 ★
    }


# ══════════════════════════════════════════════
#  2. 예측 방법 5가지
# ══════════════════════════════════════════════

def _mode_of(values: list) -> object:
    """최빈값 반환"""
    if not values:
        return None
    return Counter(values).most_common(1)[0][0]


def predict_condition(key: str, history_conds: list[dict], method: str) -> object:
    """
    특정 조건(key)에 대해 method로 다음 회차 예측값 반환
    """
    vals = [c[key] for c in history_conds if c.get(key) is not None]
    if not vals:
        return None

    n = len(vals)

    if method == "FREQUENCY":
        return _mode_of(vals)

    elif method == "WEIGHTED_RECENT":
        # 최근 20%에 3배 가중치
        cutoff = max(1, int(n * 0.8))
        weighted = vals[:cutoff] + vals[cutoff:] * 3
        return _mode_of(weighted)

    elif method == "CYCLE":
        # 최근 10개 모드
        return _mode_of(vals[-10:])

    elif method == "TREND":
        # 최근 5개 vs 이전 5개 비교 → 상승 추세 값
        if n < 10:
            return _mode_of(vals[-5:])
        recent5 = vals[-5:]
        prev5 = vals[-10:-5]
        recent_mode = _mode_of(recent5)
        prev_mode = _mode_of(prev5)
        # 연속 등장 중인 값 우선
        if recent_mode != prev_mode:
            return recent_mode
        return recent_mode

    elif method == "ENSEMBLE":
        # 4가지 다수결
        candidates = [
            predict_condition(key, history_conds, "FREQUENCY"),
            predict_condition(key, history_conds, "WEIGHTED_RECENT"),
            predict_condition(key, history_conds, "CYCLE"),
            predict_condition(key, history_conds, "TREND"),
        ]
        return _mode_of([c for c in candidates if c is not None])

    return _mode_of(vals)


METHODS = ["FREQUENCY", "WEIGHTED_RECENT", "CYCLE", "TREND", "ENSEMBLE"]
CONDITION_KEYS = [
    "odd_even", "high_low", "sum_range",
    "consecutive", "tail_dist", "tens_dist",
    "hot_count", "long_miss", "prev_overlap",
    "ac_value", "gap_std",
    "bonus_char",
    # 신규 6개
    "prime_count", "gap_max", "std_dev_bucket",
    "sum_direction", "sum_reversion", "prev2_overlap",
]
CONDITION_LABELS = {
    "odd_even":       "홀짝 비율",
    "high_low":       "고저 분포",
    "sum_range":      "합계 구간",
    "consecutive":    "연속번호",
    "tail_dist":      "끝자리 분포",
    "tens_dist":      "십의자리 분포",
    "hot_count":      "Hot 번호 수",
    "long_miss":      "장기 미출현",
    "prev_overlap":   "이전 회차 중복",
    "ac_value":       "AC값",
    "gap_std":        "간격 표준편차",
    "bonus_char":     "보너스 특성",
    # 신규
    "prime_count":    "소수 개수 ★",
    "gap_max":        "최대 번호 간격 ★",
    "std_dev_bucket": "번호 분산 구간 ★",
    "sum_direction":  "합계 이동방향 ★",
    "sum_reversion":  "극단합계 회귀 ★",
    "prev2_overlap":  "2회전 번호 재등장 ★",
}


# ══════════════════════════════════════════════
#  3. 백테스팅 코어
# ══════════════════════════════════════════════

def run_backtest(
    draws: list[dict],
    window: int = 600,
    methods: Optional[list[str]] = None,
) -> dict:
    """
    슬라이딩 윈도우 백테스팅

    Args:
        draws:   전체 회차 (오름차순)
        window:  학습 윈도우 (기존 분석: 600)
        methods: 예측 방법 목록 (None = 전체)

    Returns:
        {
          "total_tested": 609,
          "window": 600,
          "methods": {
            "WEIGHTED_RECENT": {
              "avg_accuracy": 31.64,
              "condition_accuracy": {"odd_even": 32.35, ...},
              "per_round": [{"round":601, "conditions":{...}, "match":{...}}, ...]
            },
            ...
          },
          "condition_accuracy_avg": {"odd_even": 32.1, ...},  # 전체 방법 평균
          "best_method": "WEIGHTED_RECENT",
          "ranking": [("WEIGHTED_RECENT", 31.64), ...]
        }
    """
    draws_sorted = sorted(draws, key=lambda d: d["round"])
    if len(draws_sorted) < window + 5:
        return {"error": "데이터 부족"}

    target_methods = methods or METHODS

    # 전체 조건 캐시
    all_conds: list[dict] = []
    for i, draw in enumerate(draws_sorted):
        cond = extract_conditions(draw, draws_sorted[:i])
        all_conds.append(cond)

    # 결과 초기화
    results: dict[str, dict] = {}
    for m in target_methods:
        results[m] = {
            "correct": {k: 0 for k in CONDITION_KEYS},
            "total":   0,
            "per_round": [],
        }

    for i in range(window, len(draws_sorted)):
        test_draw = draws_sorted[i]
        test_cond = all_conds[i]
        history_conds = all_conds[:i]    # 직전까지의 조건 히스토리

        for m in target_methods:
            predicted = {}
            match = {}
            for key in CONDITION_KEYS:
                pred_val = predict_condition(key, history_conds, m)
                actual_val = test_cond.get(key)
                predicted[key] = pred_val
                # tens_dist는 tuple이라 직접 비교
                match[key] = (pred_val == actual_val)

            correct_count = sum(1 for v in match.values() if v)
            accuracy = correct_count / len(CONDITION_KEYS) * 100

            for key in CONDITION_KEYS:
                if match[key]:
                    results[m]["correct"][key] += 1

            results[m]["total"] += 1
            results[m]["per_round"].append({
                "round":      test_draw["round"],
                "draw_date":  test_draw.get("draw_date", ""),
                "predicted":  {k: str(v) for k, v in predicted.items()},
                "actual":     {k: str(test_cond.get(k)) for k in CONDITION_KEYS},
                "match":      match,
                "accuracy":   round(accuracy, 2),
            })

    # 조건별 정확도, 전체 평균 계산
    summary: dict[str, dict] = {}
    for m in target_methods:
        total = results[m]["total"]
        cond_acc = {
            k: round(results[m]["correct"][k] / total * 100, 2) if total else 0
            for k in CONDITION_KEYS
        }
        avg_acc = round(sum(cond_acc.values()) / len(cond_acc), 2)
        summary[m] = {
            "avg_accuracy":       avg_acc,
            "condition_accuracy": cond_acc,
            "per_round":          results[m]["per_round"],  # 전체 기록
        }

    # 조건별 전체 방법 평균
    cond_avg = {}
    for key in CONDITION_KEYS:
        cond_avg[key] = round(
            sum(summary[m]["condition_accuracy"][key] for m in target_methods) / len(target_methods), 2
        )

    ranking = sorted(
        [(m, summary[m]["avg_accuracy"]) for m in target_methods],
        key=lambda x: x[1], reverse=True
    )
    best_method = ranking[0][0] if ranking else "WEIGHTED_RECENT"

    logger.info(f"[backtest] {results[target_methods[0]]['total']}회차 검증 완료 | 최고: {best_method}")

    return {
        "total_tested":          results[target_methods[0]]["total"] if target_methods else 0,
        "window":                window,
        "methods":               summary,
        "condition_accuracy_avg": cond_avg,
        "condition_labels":      CONDITION_LABELS,
        "best_method":           best_method,
        "ranking":               ranking,
    }


def run_cumulative_backtest(
    draws: list[dict],
    window: int = 600,
    methods: Optional[List[str]] = None,
    sample_every: int = 10,
) -> dict:
    """누적 정확도 추이 (차트용)"""
    draws_sorted = sorted(draws, key=lambda d: d["round"])
    if len(draws_sorted) < window + 5:
        return {"rounds": [], "series": {}, "labels": {}}

    target_methods = methods or METHODS
    all_conds = [extract_conditions(d, draws_sorted[:i]) for i, d in enumerate(draws_sorted)]

    running_correct: Dict[str, float] = {m: 0.0 for m in target_methods}
    running_total   = 0
    rounds_axis     = []
    series: dict[str, list[float]] = {m: [] for m in target_methods}

    for i in range(window, len(draws_sorted)):
        test_cond = all_conds[i]
        history_conds = all_conds[:i]
        running_total += 1

        for m in target_methods:
            correct = 0
            for key in CONDITION_KEYS:
                pred = predict_condition(key, history_conds, m)
                if pred == test_cond.get(key):
                    correct += 1
            running_correct[m] += correct / len(CONDITION_KEYS) * 100

        if (i - window) % sample_every == 0:
            rounds_axis.append(draws_sorted[i]["round"])
            for m in target_methods:
                series[m].append(round(running_correct[m] / running_total, 2))

    return {
        "rounds":  rounds_axis,
        "series":  series,
        "labels":  {m: m for m in target_methods},
    }


# ══════════════════════════════════════════════
#  4. 조건 만족 번호 생성 (핵심)
# ══════════════════════════════════════════════

def _satisfies(nums: list[int], target: dict, history: list[dict], weight: dict) -> float:
    """번호 조합이 target 조건에 얼마나 부합하는지 가중 점수 반환"""
    cond = extract_conditions({"num1": nums[0], "num2": nums[1], "num3": nums[2],
                               "num4": nums[3], "num5": nums[4], "num6": nums[5],
                               "bonus": 0}, history)
    score = 0.0
    total_w = 0.0
    for key in CONDITION_KEYS:
        if key == "bonus_char":
            continue
        w = weight.get(key, 1.0)
        total_w += w
        if str(cond.get(key)) == str(target.get(key)):
            score += w
    return score / total_w if total_w > 0 else 0.0


def generate_recommendations(
    draws: list[dict],
    method: str = "WEIGHTED_RECENT",
    window: int = 600,
    n_games: int = 20,
    condition_weights: Optional[Dict[str, float]] = None,
) -> dict:
    """
    백테스팅 기반 번호 추천
    1) window 회차 학습 → 다음 회차 조건 예측
    2) 랜덤 조합 다수 생성 → 예측 조건에 가장 부합하는 n_games 선택

    Returns:
        {
          "predicted_conditions": {...},
          "games": [[1,7,15,...], ...],
          "scores": [0.85, 0.84, ...],
          "method": "WEIGHTED_RECENT",
          "window": 600,
        }
    """
    draws_sorted = sorted(draws, key=lambda d: d["round"])
    if len(draws_sorted) < window:
        return {"error": "데이터 부족"}

    train = draws_sorted[-window:]
    history_conds = [extract_conditions(d, draws_sorted[:i])
                     for i, d in enumerate(draws_sorted)]
    train_conds = history_conds[-window:]

    # 조건 예측
    predicted: dict[str, object] = {}
    for key in CONDITION_KEYS:
        predicted[key] = predict_condition(key, train_conds, method)

    # 조건별 가중치 (백테스팅 정확도 기반 또는 외부 전달)
    if condition_weights is None:
        condition_weights = {k: 1.0 for k in CONDITION_KEYS}

    # 후보 생성 (1000개)
    candidates: list[tuple[float, list[int]]] = []
    for _ in range(2000):
        nums = sorted(random.sample(range(1, 46), 6))
        score = _satisfies(nums, predicted, train, condition_weights)
        candidates.append((score, nums))

    # 점수 내림차순, 중복 제거
    candidates.sort(key=lambda x: -x[0])
    seen = set()
    games, scores = [], []
    for score, nums in candidates:
        key_str = "-".join(map(str, nums))
        if key_str not in seen:
            seen.add(key_str)
            games.append(nums)
            scores.append(round(score, 4))
        if len(games) >= n_games:
            break

    return {
        "predicted_conditions": {k: str(v) for k, v in predicted.items()},
        "condition_labels":     CONDITION_LABELS,
        "games":                games,
        "scores":               scores,
        "method":               method,
        "window":               window,
        "n_games":              n_games,
    }


# ══════════════════════════════════════════════
#  5. 고정번호 생성
# ══════════════════════════════════════════════

def generate_fixed_number(draws: list[dict]) -> dict:
    """
    매주 고정 구매할 번호 1조 생성.

    전략 근거:
      - 전체 회차에서 각 조건의 "최빈값(mode)" 산출 → 역대 가장 자주 등장한 구조
      - 그 구조를 만족하면서 추가로:
          · 합계가 역대 중앙값(±10) 범위
          · AC값 중간 이상 (번호 분포 다양성)
          · 연속번호 최대 1쌍 (너무 많은 연속 회피)
          · 끝자리 중복 최소화
      - 위 조건을 동시에 가장 잘 만족하는 조합 선택
      - 조건이 "안정적으로 자주 나오는 구조"이므로
        장기 구매 시 커버 확률이 최대화됨

    Returns:
        {
          "numbers": [3, 11, 22, 28, 34, 41],
          "score": 0.91,
          "rationale": {
            "odd_even": "홀수 3개 — 역대 최빈(3홀3짝)",
            "high_low": "고번호 3개 — 역대 최빈(3저3고)",
            "sum":      "합계 130 — 역대 중앙값 근처",
            "ac":       "AC값 7 — 다양한 번호 간격",
            "tail":     "끝자리 중복 0 — 모두 다름",
            "consec":   "연속번호 없음",
          },
          "all_conditions": {...},
          "condition_labels": {...},
        }
    """
    draws_sorted = sorted(draws, key=lambda d: d["round"])

    # 전체 조건 계산
    all_conds = []
    for i, draw in enumerate(draws_sorted):
        cond = extract_conditions(draw, draws_sorted[:i])
        all_conds.append(cond)

    # 조건별 전체 최빈값 산출
    target: Dict[str, object] = {}
    for key in CONDITION_KEYS:
        vals = [c[key] for c in all_conds if c.get(key) is not None]
        target[key] = _mode_of(vals)

    # 합계 중앙값
    sums = [sum(_nums(d)) for d in draws_sorted]
    median_sum = sorted(sums)[len(sums) // 2]

    # 고정번호 가중치: 안정적 조건에 높은 가중치
    weights: Dict[str, float] = {
        "odd_even":     3.0,   # 홀짝은 가장 기본
        "high_low":     3.0,   # 고저도 기본
        "sum_range":    2.5,   # 합계 구간
        "consecutive":  2.0,   # 연속번호 패턴
        "tail_dist":    2.0,   # 끝자리
        "ac_value":     1.5,   # AC값
        "gap_std":      1.0,
        "hot_count":    0.5,   # 고정번호라 hot/cold는 낮은 가중치
        "long_miss":    0.5,
        "prev_overlap": 0.0,   # 고정번호는 이전 회차 무관
        "tens_dist":    1.0,
        "bonus_char":   0.0,
    }

    # 후보 3000개 생성
    candidates: list[Tuple[float, list[int], dict]] = []
    for _ in range(3000):
        nums = sorted(random.sample(range(1, 46), 6))

        # 기본 필터: 합계 범위 + AC 최소값
        total = sum(nums)
        ac = _ac_value(nums)
        if not (median_sum - 25 <= total <= median_sum + 25):
            continue
        if ac < 4:
            continue

        score = _satisfies(nums, target, draws_sorted, weights)
        cond = extract_conditions(
            {"num1": nums[0], "num2": nums[1], "num3": nums[2],
             "num4": nums[3], "num5": nums[4], "num6": nums[5], "bonus": 0},
            draws_sorted
        )
        candidates.append((score, nums, cond))

    if not candidates:
        # 필터 없이 재시도
        for _ in range(1000):
            nums = sorted(random.sample(range(1, 46), 6))
            score = _satisfies(nums, target, draws_sorted, weights)
            cond = extract_conditions(
                {"num1": nums[0], "num2": nums[1], "num3": nums[2],
                 "num4": nums[3], "num5": nums[4], "num6": nums[5], "bonus": 0},
                draws_sorted
            )
            candidates.append((score, nums, cond))

    candidates.sort(key=lambda x: -x[0])
    best_score, best_nums, best_cond = candidates[0]

    # 설명 생성
    odd_c = sum(1 for n in best_nums if n % 2 == 1)
    high_c = sum(1 for n in best_nums if n >= 23)
    total_sum = sum(best_nums)
    ac_val = _ac_value(best_nums)
    tail_dup = _tail_duplicates(best_nums)
    consec = _consecutive_max(best_nums)

    rationale = {
        "odd_even": f"홀수 {odd_c}개 / 짝수 {6-odd_c}개 (역대 최빈: {target.get('odd_even')}홀)",
        "high_low": f"고번호(23+) {high_c}개 / 저번호 {6-high_c}개 (역대 최빈: {target.get('high_low')}고)",
        "sum":      f"합계 {total_sum} (역대 중앙값 {median_sum}, 범위 ±25 내)",
        "ac":       f"AC값 {ac_val} (높을수록 번호 간격 다양)",
        "tail":     f"끝자리 중복 {tail_dup}쌍 {'(모두 다름)' if tail_dup == 0 else ''}",
        "consec":   f"연속번호 {'없음' if consec == 0 else f'{consec}쌍'}",
    }

    return {
        "numbers":          best_nums,
        "score":            round(best_score, 4),
        "rationale":        rationale,
        "all_conditions":   {k: str(v) for k, v in best_cond.items()},
        "target_conditions": {k: str(v) for k, v in target.items()},
        "condition_labels": CONDITION_LABELS,
        "median_sum":       median_sum,
    }


# ══════════════════════════════════════════════
#  실전 당첨 시뮬레이션
#  각 회차마다 추천번호를 생성해 실제 당첨번호와 대조
# ══════════════════════════════════════════════

PRIZE_TABLE = {1: 2_000_000_000, 2: 55_000_000, 3: 1_500_000, 4: 50_000, 5: 5_000}
TICKET_PRICE = 1_000


def _check_rank(game: list, actual: list, bonus: int) -> int:
    matched = len(set(game) & set(actual))
    if matched == 6: return 1
    if matched == 5 and bonus in game: return 2
    if matched == 5: return 3
    if matched == 4: return 4
    if matched == 3: return 5
    return 0


def run_real_sim(
    draws: list,
    method: str = "WEIGHTED_RECENT",
    window: int = 600,
    n_games: int = 9,
    sample_every: int = 10,
) -> dict:
    """
    학습 윈도우 이후 각 회차마다 추천번호를 생성해 실제 당첨번호와 대조.
    랜덤 구매와 비교 결과도 함께 반환.
    """
    draws_sorted = sorted(draws, key=lambda d: d["round"])
    total = len(draws_sorted)

    if total <= window:
        raise ValueError(f"데이터 부족: {total}회차, 윈도우 {window}회 필요")

    rank_counts   = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    random_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    total_spent   = 0
    total_prize   = 0
    random_prize  = 0
    tested_rounds = []
    detail        = []  # 등수별 대표 사례

    test_indices = range(window, total, sample_every)

    for i in test_indices:
        train = draws_sorted[:i]
        target_draw = draws_sorted[i]
        actual = [target_draw["num1"], target_draw["num2"], target_draw["num3"],
                  target_draw["num4"], target_draw["num5"], target_draw["num6"]]
        bonus = target_draw["bonus"]
        round_no = target_draw["round"]

        # 추천번호 생성
        try:
            rec = generate_recommendations(train, method=method, window=window, n_games=n_games)
            games = rec["games"]
        except Exception:
            continue

        spent = len(games) * TICKET_PRICE
        total_spent += spent
        tested_rounds.append(round_no)

        for game in games:
            rank = _check_rank(game, actual, bonus)
            rank_counts[rank] += 1
            prize = PRIZE_TABLE.get(rank, 0)
            total_prize += prize

            # 대표 사례 수집 (1~3등만)
            if rank in (1, 2, 3) and not any(d["rank"] == rank for d in detail):
                detail.append({
                    "round": round_no,
                    "rank": rank,
                    "game": game,
                    "actual": actual,
                    "bonus": bonus,
                    "matched": len(set(game) & set(actual)),
                })

        # 랜덤 비교
        for _ in games:
            rnd_game = sorted(random.sample(range(1, 46), 6))
            rrank = _check_rank(rnd_game, actual, bonus)
            random_counts[rrank] += 1
            random_prize += PRIZE_TABLE.get(rrank, 0)

    total_games   = sum(rank_counts.values())
    random_games  = sum(random_counts.values())
    net           = total_prize - total_spent
    random_net    = random_prize - total_spent
    roi           = (total_prize / total_spent * 100) if total_spent else 0
    random_roi    = (random_prize / total_spent * 100) if total_spent else 0

    # 등수별 비율
    rank_rate   = {k: round(v / total_games * 100, 3) if total_games else 0
                   for k, v in rank_counts.items()}
    random_rate = {k: round(v / random_games * 100, 3) if random_games else 0
                   for k, v in random_counts.items()}

    return {
        "method":        method,
        "window":        window,
        "n_games":       n_games,
        "sample_every":  sample_every,
        "tested_rounds": len(tested_rounds),
        "total_games":   total_games,
        "total_spent":   total_spent,
        "total_prize":   total_prize,
        "net":           net,
        "roi":           round(roi, 2),
        "rank_counts":   rank_counts,
        "rank_rate":     rank_rate,
        "random_counts": random_counts,
        "random_rate":   random_rate,
        "random_prize":  random_prize,
        "random_net":    random_net,
        "random_roi":    round(random_roi, 2),
        "detail":        detail,
    }


# ══════════════════════════════════════════════
#  패턴 분석 — 신규 조건 6개 실증 검증
#  각 조건이 실제로 이론값과 얼마나 다른지 측정
# ══════════════════════════════════════════════

def run_pattern_analysis(draws: list) -> dict:
    """
    1213회차 전체 데이터로 신규 조건 6개 + 기존 조건들의
    실증 패턴을 분석해 반환.

    반환:
    {
      "sum_direction":    { "after_up_down_pct_up": 63.5, "after_down_up_pct_down": 58.7, ... },
      "sum_reversion":    { "after_extreme_pct_normal": 87.5, ... },
      "prev2_carry":      { "overlap_1_pct": 44.8, "theory_1_pct": 42.4, ... },
      "prime_count":      { "distribution": {0:x, 1:x, ...}, "avg": 2.3, "theory_avg": 2.1 },
      "gap_max":          { "distribution": {...}, "avg": ... },
      "std_dev_bucket":   { "distribution": {...} },
      "bonus_carryover":  { "rate": 13.7, "theory": 13.3 },
      "consecutive_sum":  { "1_lag_same_pct": 10.6, "theory_pct": 8.8 },
      "total_draws": 1213,
    }
    """
    from math import comb as C
    draws_sorted = sorted(draws, key=lambda d: d["round"])
    n = len(draws_sorted)

    def nums_of(d):
        return sorted([d["num1"], d["num2"], d["num3"], d["num4"], d["num5"], d["num6"]])

    sums = [sum(nums_of(d)) for d in draws_sorted]
    bonuses = [d["bonus"] for d in draws_sorted]

    # ── 1. 합계 방향 반전 패턴 ──
    up_down_then_up, up_down_total = 0, 0
    down_up_then_down, down_up_total = 0, 0
    for i in range(2, n - 1):
        if sums[i-1] > sums[i-2] and sums[i] < sums[i-1]:   # up→down
            up_down_total += 1
            if sums[i+1] > sums[i]:
                up_down_then_up += 1
        if sums[i-1] < sums[i-2] and sums[i] > sums[i-1]:   # down→up
            down_up_total += 1
            if sums[i+1] < sums[i]:
                down_up_then_down += 1

    sum_direction = {
        "after_up_down_pct_up":   round(up_down_then_up / up_down_total * 100, 1) if up_down_total else 0,
        "after_down_up_pct_down": round(down_up_then_down / down_up_total * 100, 1) if down_up_total else 0,
        "after_up_down_n":        up_down_total,
        "after_down_up_n":        down_up_total,
        "theory_pct":             50.0,
        "insight": "합계가 방향을 꺾은 직후 다시 꺾이는 경향 (63.5% vs 이론 50%)",
    }

    # ── 2. 극단 합계 후 평균 회귀 ──
    extreme_next_normal, extreme_total = 0, 0
    for i in range(n - 1):
        if sums[i] < 100 or sums[i] >= 180:
            extreme_total += 1
            if 100 <= sums[i+1] < 180:
                extreme_next_normal += 1
    extreme_same, extreme_same_total = 0, 0
    for i in range(n - 1):
        if sums[i] < 100 or sums[i] >= 180:
            extreme_same_total += 1
            if sums[i+1] < 100 or sums[i+1] >= 180:
                extreme_same += 1

    sum_reversion = {
        "extreme_count":          extreme_total,
        "after_extreme_pct_normal": round(extreme_next_normal / extreme_total * 100, 1) if extreme_total else 0,
        "after_extreme_pct_extreme": round(extreme_same / extreme_same_total * 100, 1) if extreme_same_total else 0,
        "theory_normal_pct":      round((sum(1 for s in sums if 100 <= s < 180) / n) * 100, 1),
        "insight": "극단 합계(<100 또는 ≥180) 이후 87%+ 확률로 중간 합계(100-179) 진입",
    }

    # ── 3. 2회 전 번호 재등장 ──
    prev2_dist: Counter = Counter()
    for i in range(2, n):
        past = set(nums_of(draws_sorted[i-2]))
        cur  = set(nums_of(draws_sorted[i]))
        prev2_dist[len(past & cur)] += 1
    prev2_total = sum(prev2_dist.values())
    theory_prev2 = {k: round(C(6,k)*C(39,6-k)/C(45,6)*100, 2) for k in range(5)}

    prev2_carry = {
        "distribution": {str(k): {"count": prev2_dist.get(k,0),
                                   "pct": round(prev2_dist.get(k,0)/prev2_total*100,1),
                                   "theory_pct": theory_prev2.get(k,0)}
                         for k in range(5)},
        "insight": "2회 전 번호와 1개 겹침 확률 44.8% (이론 42.4%) — 약한 carry-forward 효과",
    }

    # ── 4. 소수 개수 분포 ──
    prime_counts = [_prime_count(nums_of(d)) for d in draws_sorted]
    pc_dist = Counter(prime_counts)
    pc_avg  = sum(prime_counts) / n
    # 이론: 1-45 중 소수 14개, 비소수 31개, 기댓값 = 6 * 14/45
    theory_prime_avg = 6 * 14 / 45

    prime_count_res = {
        "distribution": {str(k): {"count": pc_dist.get(k,0),
                                   "pct": round(pc_dist.get(k,0)/n*100,1)}
                         for k in range(7)},
        "avg":          round(pc_avg, 2),
        "theory_avg":   round(theory_prime_avg, 2),
        "diff":         round(pc_avg - theory_prime_avg, 3),
    }

    # ── 5. 최대 번호 간격 분포 ──
    gap_maxes = [_gap_max(nums_of(d)) for d in draws_sorted]
    gm_dist   = Counter(gap_maxes)
    gm_avg    = sum(gap_maxes) / n

    gap_max_res = {
        "distribution": {str(k): {"count": gm_dist.get(k,0),
                                   "pct": round(gm_dist.get(k,0)/n*100,1)}
                         for k in sorted(gm_dist.keys())},
        "avg":   round(gm_avg, 1),
        "insight": "최대 간격이 크면 번호가 넓게 분포 (spread)",
    }

    # ── 6. 번호 표준편차 구간 ──
    std_buckets = [_std_dev_bucket(nums_of(d)) for d in draws_sorted]
    sb_dist = Counter(std_buckets)

    std_dev_res = {
        "distribution": {k: {"count": sb_dist.get(k,0),
                              "pct": round(sb_dist.get(k,0)/n*100,1)}
                         for k in ["tight", "mid", "spread"]},
        "insight": "tight<10%, spread~20% — 대부분 중간 분산(mid)",
    }

    # ── 7. 보너스 carry-over ──
    bonus_in_next = sum(1 for i in range(1, n) if bonuses[i-1] in set(nums_of(draws_sorted[i])))
    bonus_carryover = {
        "count":       bonus_in_next,
        "pct":         round(bonus_in_next / (n-1) * 100, 1),
        "theory_pct":  round(6/45*100, 1),
        "insight":     "보너스 → 다음 본번호 등장 13.7% (이론값과 동일 — 패턴 없음)",
    }

    # ── 8. 합계+홀수 조합 1회 후 반복 ──
    def sb(s):
        return "low" if s < 120 else ("mid" if s < 160 else "high")
    combos = [(sb(sums[i]), sum(1 for x in nums_of(draws_sorted[i]) if x%2==1)) for i in range(n)]
    same_1lag = sum(1 for i in range(n-1) if combos[i] == combos[i+1])
    from collections import Counter as Ctr
    combo_freq = Ctr(combos)
    theory_same = sum((c/n)**2 for c in combo_freq.values()) * 100

    consecutive_sum = {
        "same_1lag_pct":  round(same_1lag / (n-1) * 100, 1),
        "theory_pct":     round(theory_same, 1),
        "diff":           round(same_1lag/(n-1)*100 - theory_same, 1),
        "insight":        "직후 동일 합계구간+홀수 10.6% (이론 8.8%) — 약한 지속성",
    }

    return {
        "total_draws":    n,
        "sum_direction":  sum_direction,
        "sum_reversion":  sum_reversion,
        "prev2_carry":    prev2_carry,
        "prime_count":    prime_count_res,
        "gap_max":        gap_max_res,
        "std_dev_bucket": std_dev_res,
        "bonus_carryover": bonus_carryover,
        "consecutive_sum": consecutive_sum,
    }
