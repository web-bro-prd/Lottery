"""
연금복권720+ 번호 추천 엔진 v3
────────────────────────────────────────────────────────────
핵심 설계 원칙:
  - 최종 추천은 조+번호 1개 조합만 출력
    (연금복권은 같은 조+번호를 5장 구매하는 구조)
  - 4가지 전략으로 후보 20개 생성 후, 점수 계산으로 최고 1개 선택

점수 기준 (0~100점):
  1. 자릿수 빈도 점수 (최근 50회 기준, 앞자리 2배 가중)
  2. 합계 근접 점수 (역대 평균에 가까울수록 높음)
  3. 앞자리 일치 보너스 (최근 10회 당첨번호와 앞 2~4자리 일치 → 3~5등 가능성)

등수 구조:
  1등: 조 일치 + 6자리 모두 일치
  2등: 조 불일치 + 6자리 모두 일치
  3등: 앞 5자리 일치
  4등: 앞 4자리 일치
  5등: 앞 3자리 일치
  6등: 앞 2자리 일치
  7등: 끝 1자리 일치
"""
import random
import statistics
from collections import Counter
from typing import Optional


# ──────────────────────────────────────────────────
# 내부 유틸
# ──────────────────────────────────────────────────

def _build_pos_counts(draws: list, recent_n: Optional[int] = None) -> list:
    src = draws[-recent_n:] if recent_n and len(draws) >= recent_n else draws
    counters = [Counter() for _ in range(6)]
    for draw in src:
        num = str(draw["num"]).zfill(6)
        for pos, ch in enumerate(num):
            counters[pos][ch] += 1
    return counters


def _build_grp_counts(draws: list, recent_n: Optional[int] = None) -> Counter:
    src = draws[-recent_n:] if recent_n and len(draws) >= recent_n else draws
    return Counter(str(d["grp"]) for d in src)


def _weighted_digit(counter: Counter, bias: float = 1.0) -> str:
    digits = [str(i) for i in range(10)]
    weights = [(counter.get(d, 0) + 1) ** bias for d in digits]
    return random.choices(digits, weights=weights, k=1)[0]


# ──────────────────────────────────────────────────
# 조(grp) 선택
# ──────────────────────────────────────────────────

def _select_grp(draws: list) -> int:
    """
    전체 빈도(1배) + 최근 100회 빈도(2배) 합산.
    최근 5회에 연속 등장한 조는 가중치 0.3배 억제.
    """
    if not draws:
        return random.randint(1, 5)

    all_counts = _build_grp_counts(draws)
    rec_counts = _build_grp_counts(draws, recent_n=100)
    last5_grps = {str(d["grp"]) for d in draws[-5:]}

    weights = []
    for g in range(1, 6):
        gs = str(g)
        w = (all_counts.get(gs, 0) + 1) + 2 * (rec_counts.get(gs, 0) + 1)
        if gs in last5_grps:
            w *= 0.3
        weights.append(w)

    return int(random.choices(range(1, 6), weights=weights, k=1)[0])


# ──────────────────────────────────────────────────
# 후보 번호 생성 전략들
# ──────────────────────────────────────────────────

def _gen_hot(draws: list, grp: int, recent_n: int = 50) -> dict:
    """최근 빈도 기반, 앞자리 bias 강화"""
    counters = _build_pos_counts(draws, recent_n=recent_n)
    digits = [
        _weighted_digit(c, bias=2.0 if pos < 3 else 1.2)
        for pos, c in enumerate(counters)
    ]
    return {"grp": grp, "num": "".join(digits), "strategy": "hot"}


def _gen_prefix_fix(draws: list, grp: int) -> dict:
    """최근 당첨번호 앞 N자리 고정 + 나머지 빈도 변형 (3~5등 공략)"""
    if not draws:
        return {"grp": grp, "num": str(random.randint(0, 999999)).zfill(6), "strategy": "prefix_fix"}
    base_num = str(random.choice(draws[-5:])["num"]).zfill(6)
    fix_len  = random.choices([2, 3, 4], weights=[2, 3, 5], k=1)[0]
    counters = _build_pos_counts(draws, recent_n=100)
    digits   = list(base_num[:fix_len])
    for pos in range(fix_len, 6):
        digits.append(_weighted_digit(counters[pos], bias=1.5))
    return {"grp": grp, "num": "".join(digits), "strategy": "prefix_fix"}


def _gen_sum_range(draws: list, grp: int) -> dict:
    """역대 합계 평균 ± σ 범위 내 번호 생성"""
    if not draws:
        return {"grp": grp, "num": str(random.randint(0, 999999)).zfill(6), "strategy": "sum_range"}
    sums = [sum(int(c) for c in str(d["num"]).zfill(6)) for d in draws]
    avg  = statistics.mean(sums)
    std  = statistics.stdev(sums) if len(sums) > 1 else 5.0
    counters = _build_pos_counts(draws)
    for attempt in range(300):
        sigma = 0.8 + (attempt // 50) * 0.4
        digits  = [_weighted_digit(c, bias=1.5) for c in counters]
        num_str = "".join(digits)
        if avg - sigma * std <= sum(int(c) for c in num_str) <= avg + sigma * std:
            return {"grp": grp, "num": num_str, "strategy": "sum_range"}
    return {"grp": grp, "num": "".join(_weighted_digit(c) for c in counters), "strategy": "sum_range"}


def _gen_cold_hot(draws: list, grp: int, recent_n: int = 30) -> dict:
    """앞 3자리 핫 + 뒤 3자리 콜드 혼합"""
    hot_c  = _build_pos_counts(draws, recent_n=50)
    all_c  = _build_pos_counts(draws)
    cold_c = _build_pos_counts(draws, recent_n=recent_n)
    digits = []
    for pos in range(6):
        if pos < 3:
            digits.append(_weighted_digit(hot_c[pos], bias=2.0))
        else:
            d_list  = [str(i) for i in range(10)]
            weights = [max(1, (all_c[pos].get(d, 0) + 1) - cold_c[pos].get(d, 0)) for d in d_list]
            digits.append(random.choices(d_list, weights=weights, k=1)[0])
    return {"grp": grp, "num": "".join(digits), "strategy": "cold_hot"}


# ──────────────────────────────────────────────────
# 점수 계산
# ──────────────────────────────────────────────────

def _score(candidate: dict, draws: list, hot_counters: list, avg_sum: float, std_sum: float) -> float:
    """
    후보 1개에 대한 점수 계산 (높을수록 좋음).

    1. 자릿수 빈도 점수 (0~50점)
       - 각 자릿수에서 해당 숫자의 최근 50회 출현 비율
       - 앞 3자리는 2배 가중 (고등수 결정 자리)

    2. 합계 근접 점수 (0~30점)
       - 역대 합계 평균에서 벗어날수록 감점
       - |합계 - 평균| / std 가 0이면 30점, 2 이상이면 0점

    3. 앞자리 일치 보너스 (0~20점)
       - 최근 10회 당첨번호와 앞 2~4자리 일치 여부
       - 일치 자릿수 × 5점 (최대 20점, 4자리 일치)
    """
    num = candidate["num"]
    total = len(draws)
    if total == 0:
        return 0.0

    # 1. 자릿수 빈도 점수
    freq_score = 0.0
    recent_total = min(50, total)
    for pos, ch in enumerate(num):
        cnt = hot_counters[pos].get(ch, 0)
        pct = cnt / recent_total  # 0~1
        weight = 2.0 if pos < 3 else 1.0
        freq_score += pct * weight
    # 정규화: 최대 가중치 합 = 2*3 + 1*3 = 9, pct 최대 1.0 → 9.0
    freq_score = (freq_score / 9.0) * 50

    # 2. 합계 근접 점수
    num_sum = sum(int(c) for c in num)
    if std_sum > 0:
        z = abs(num_sum - avg_sum) / std_sum
    else:
        z = 0.0
    sum_score = max(0.0, 30.0 * (1 - z / 2))

    # 3. 앞자리 일치 보너스
    prefix_bonus = 0.0
    recent10 = [str(d["num"]).zfill(6) for d in draws[-10:]]
    for ref in recent10:
        for match_len in range(4, 1, -1):  # 4자리, 3자리, 2자리 순
            if num[:match_len] == ref[:match_len]:
                prefix_bonus = max(prefix_bonus, match_len * 5.0)
                break
    prefix_bonus = min(prefix_bonus, 20.0)

    return freq_score + sum_score + prefix_bonus


# ──────────────────────────────────────────────────
# 공개 API
# ──────────────────────────────────────────────────

def weekly_pension_pick(draws: list) -> dict:
    """
    이번 주 연금복권 최적 추천 1개 반환.

    1. 조(grp) 선택
    2. 4가지 전략으로 후보 20개 생성
    3. 점수 계산 → 최고 점수 1개 선택

    반환: {"grp": int, "num": "xxxxxx", "strategy": str, "score": float}
    """
    if not draws:
        grp = random.randint(1, 5)
        return {"grp": grp, "num": str(random.randint(0, 999999)).zfill(6), "strategy": "random", "score": 0.0}

    grp          = _select_grp(draws)
    hot_counters = _build_pos_counts(draws, recent_n=50)
    sums         = [sum(int(c) for c in str(d["num"]).zfill(6)) for d in draws]
    avg_sum      = statistics.mean(sums)
    std_sum      = statistics.stdev(sums) if len(sums) > 1 else 5.0

    # 후보 생성: 전략별 5개씩 → 총 20개
    candidates = []
    for _ in range(5):
        candidates.append(_gen_hot(draws, grp))
        candidates.append(_gen_prefix_fix(draws, grp))
        candidates.append(_gen_sum_range(draws, grp))
        candidates.append(_gen_cold_hot(draws, grp))

    # 점수 계산
    scored = [
        {**c, "score": round(_score(c, draws, hot_counters, avg_sum, std_sum), 2)}
        for c in candidates
    ]
    best = max(scored, key=lambda x: x["score"])
    return best


def recommend_all_pension(draws: list, games: int = 3) -> dict:
    """
    API용: 3가지 전략 각각의 최선 1개씩 반환 (웹 추천 페이지용).
    각 전략 그룹 내에서도 동일 조 사용.
    """
    grp = _select_grp(draws)
    hot_counters = _build_pos_counts(draws, recent_n=50)
    sums = [sum(int(c) for c in str(d["num"]).zfill(6)) for d in draws]
    avg_sum = statistics.mean(sums) if sums else 27.0
    std_sum = statistics.stdev(sums) if len(sums) > 1 else 5.0

    def _best_of(gen_fn, n=5):
        candidates = [gen_fn(draws, grp) for _ in range(n)]
        scored = [{**c, "score": round(_score(c, draws, hot_counters, avg_sum, std_sum), 2)} for c in candidates]
        return max(scored, key=lambda x: x["score"])

    freq_games = [_best_of(_gen_hot) for _ in range(games)]
    bal_games  = [_best_of(_gen_sum_range) for _ in range(games)]
    rand_grp   = random.randint(1, 5)
    rand_games = [
        {"grp": rand_grp, "num": str(random.randint(0, 999999)).zfill(6), "strategy": "random"}
        for _ in range(games)
    ]

    return {
        "frequency": {
            "games": freq_games,
            "strategy": "frequency",
            "description": "최근 자릿수별 출현 빈도 기반, 앞자리(고등수)에 강한 가중치를 부여합니다.",
        },
        "balanced": {
            "games": bal_games,
            "strategy": "balanced",
            "description": "역대 당첨번호 합계 범위 내에서 통계적으로 안정된 번호를 생성합니다.",
        },
        "random": {
            "games": rand_games,
            "strategy": "random",
            "description": "완전 무작위로 번호를 생성합니다 (동일 조 적용).",
        },
    }


# ── 레거시 호환 ───────────────────────────────────

def recommend_by_digit_frequency(draws: list, games: int = 5) -> list:
    grp = _select_grp(draws)
    return [_gen_hot(draws, grp) for _ in range(games)]


def recommend_balanced(draws: list, games: int = 5) -> list:
    grp = _select_grp(draws)
    return [_gen_sum_range(draws, grp) for _ in range(games)]


def recommend_random(games: int = 5) -> list:
    grp = random.randint(1, 5)
    return [
        {"grp": grp, "num": str(random.randint(0, 999999)).zfill(6), "strategy": "random"}
        for _ in range(games)
    ]
