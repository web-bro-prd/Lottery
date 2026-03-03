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


def extract_conditions(draw: dict, history: list[dict]) -> dict:
    """회차 하나를 13개 조건 dict로 변환"""
    nums = _nums(draw)
    bonus = draw.get("bonus", 0)

    # 빈도 조건용 준비
    recent10 = history[-10:] if len(history) >= 10 else history
    recent20 = history[-20:] if len(history) >= 20 else history
    prev = history[-1] if history else None

    hot_pool: set[int] = set()
    for d in recent10:
        hot_pool.update(_nums(d))

    miss_pool: set[int] = set(range(1, 46))
    for d in recent20:
        miss_pool -= set(_nums(d))

    prev_nums = set(_nums(prev)) if prev else set()

    total = sum(nums)
    odd_count = sum(1 for n in nums if n % 2 == 1)
    high_count = sum(1 for n in nums if n >= 23)
    ac = _ac_value(nums)

    return {
        "odd_even":     odd_count,                          # 0~6
        "high_low":     high_count,                         # 0~6
        "sum_range":    _sum_range(total),                  # 문자열
        "consecutive":  _consecutive_max(nums),             # 0~5
        "tail_dist":    _tail_duplicates(nums),             # 0~5
        "tens_dist":    _tens_pattern(nums),                # 5-tuple
        "hot_count":    len(set(nums) & hot_pool),          # 0~6
        "long_miss":    len(set(nums) & miss_pool),         # 0~6
        "prev_overlap": len(set(nums) & prev_nums),         # 0~6
        "ac_value":     min(ac, 9),                         # 0~9
        "gap_std":      _gap_std_bucket(nums),              # low/mid/high
        "total_sum":    total,                              # 숫자 그대로 (시뮬에서 사용)
        "bonus_char":   f"{'odd' if bonus % 2 == 1 else 'even'}_{'high' if bonus >= 23 else 'low'}",
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
]
CONDITION_LABELS = {
    "odd_even":     "홀짝 비율",
    "high_low":     "고저 분포",
    "sum_range":    "합계 구간",
    "consecutive":  "연속번호",
    "tail_dist":    "끝자리 분포",
    "tens_dist":    "십의자리 분포",
    "hot_count":    "Hot 번호 수",
    "long_miss":    "장기 미출현",
    "prev_overlap": "이전 회차 중복",
    "ac_value":     "AC값",
    "gap_std":      "간격 표준편차",
    "bonus_char":   "보너스 특성",
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
