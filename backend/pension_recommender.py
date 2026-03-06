"""
연금복권720+ 번호 추천 엔진 v2
────────────────────────────────────────────────────────────
핵심 설계 원칙:
  1. 조(grp)는 5게임 모두 동일 — 실제 구매 패턴 반영
     (연금복권은 같은 조+번호를 5장 구매하는 구조)
  2. 당첨 등수 구조 반영 — 앞자리 일치가 고등수이므로
     앞자리에 더 높은 빈도 가중치(bias) 부여
  3. 4가지 전략 조합으로 5게임 구성:
     A(hot×2) + B(prefix_fix×1) + C(sum_range×1) + D(cold_hot×1)

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


# ──────────────────────────────────────────────────
# 내부 유틸
# ──────────────────────────────────────────────────

def _build_pos_counts(draws: list, recent_n: int | None = None) -> list:
    """자릿수별 Counter 리스트 반환 [Counter×6]. recent_n 지정 시 최근 N회만."""
    src = draws[-recent_n:] if recent_n and len(draws) >= recent_n else draws
    counters = [Counter() for _ in range(6)]
    for draw in src:
        num = str(draw["num"]).zfill(6)
        for pos, ch in enumerate(num):
            counters[pos][ch] += 1
    return counters


def _build_grp_counts(draws: list, recent_n: int | None = None) -> Counter:
    """조별 Counter 반환"""
    src = draws[-recent_n:] if recent_n and len(draws) >= recent_n else draws
    return Counter(str(d["grp"]) for d in src)


def _weighted_digit(counter: Counter, bias: float = 1.0) -> str:
    """
    Counter 기반 가중치 선택.
    bias > 1.0 이면 빈도 높은 숫자를 더 강하게 선호.
    스무딩(+1)으로 출현 0인 숫자도 선택 가능.
    """
    digits = [str(i) for i in range(10)]
    weights = [(counter.get(d, 0) + 1) ** bias for d in digits]
    return random.choices(digits, weights=weights, k=1)[0]


# ──────────────────────────────────────────────────
# 조(grp) 선택
# ──────────────────────────────────────────────────

def _select_grp(draws: list) -> int:
    """
    조 선택 로직:
    - 전체 빈도(1배) + 최근 100회 빈도(2배) 합산 가중치
    - 최근 5회에 등장한 조는 가중치 0.3배 (과열 방지)
    - 5게임 전체에 동일한 조를 반환
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
            w *= 0.3  # 최근 5회 연속 나온 조 억제
        weights.append(w)

    return int(random.choices(range(1, 6), weights=weights, k=1)[0])


# ──────────────────────────────────────────────────
# 전략 A: 핫 빈도 기반 (앞자리 bias 강화)
# ──────────────────────────────────────────────────

def _strategy_hot(draws: list, grp: int, recent_n: int = 50) -> dict:
    """
    최근 recent_n회 자릿수별 빈도 기반.
    앞 3자리(고등수 결정 자리)에 bias=2.0, 뒤 3자리에 bias=1.2 적용.
    """
    counters = _build_pos_counts(draws, recent_n=recent_n)
    digits = []
    for pos, counter in enumerate(counters):
        bias = 2.0 if pos < 3 else 1.2
        digits.append(_weighted_digit(counter, bias=bias))
    return {"grp": grp, "num": "".join(digits), "strategy": "hot"}


# ──────────────────────────────────────────────────
# 전략 B: 앞자리 고정 + 뒷자리 변형 (3~5등 직접 공략)
# ──────────────────────────────────────────────────

def _strategy_prefix_fix(draws: list, grp: int) -> dict:
    """
    최근 당첨번호의 앞 N자리를 고정하고 나머지를 빈도 기반으로 채움.
    fix_len은 2~4 중 가중 랜덤 (4자리 고정 = 4등 노림이 가장 많음).
    최근 3회 번호 중 하나를 베이스로 선택.
    """
    if not draws:
        return {"grp": grp, "num": str(random.randint(0, 999999)).zfill(6), "strategy": "prefix_fix"}

    base_num = str(random.choice(draws[-3:])["num"]).zfill(6)
    fix_len  = random.choices([2, 3, 4], weights=[2, 3, 5], k=1)[0]

    counters = _build_pos_counts(draws, recent_n=100)
    digits   = list(base_num[:fix_len])
    for pos in range(fix_len, 6):
        digits.append(_weighted_digit(counters[pos], bias=1.5))

    return {"grp": grp, "num": "".join(digits), "strategy": "prefix_fix"}


# ──────────────────────────────────────────────────
# 전략 C: 합계 범위 기반 (통계적 필터링)
# ──────────────────────────────────────────────────

def _strategy_sum_range(draws: list, grp: int) -> dict:
    """
    역대 당첨번호 6자리 합계의 평균 ± 0.8σ 범위 내 번호를 생성.
    50회마다 sigma를 0.4씩 확대 (무한루프 방지).
    """
    if not draws:
        return {"grp": grp, "num": str(random.randint(0, 999999)).zfill(6), "strategy": "sum_range"}

    sums = [sum(int(c) for c in str(d["num"]).zfill(6)) for d in draws]
    avg  = statistics.mean(sums)
    std  = statistics.stdev(sums) if len(sums) > 1 else 5.0

    counters = _build_pos_counts(draws)

    for attempt in range(300):
        sigma   = 0.8 + (attempt // 50) * 0.4
        lo, hi  = avg - sigma * std, avg + sigma * std
        digits  = [_weighted_digit(c, bias=1.5) for c in counters]
        num_str = "".join(digits)
        if lo <= sum(int(c) for c in num_str) <= hi:
            return {"grp": grp, "num": num_str, "strategy": "sum_range"}

    # 최후 폴백
    return {"grp": grp, "num": "".join(_weighted_digit(c) for c in counters), "strategy": "sum_range"}


# ──────────────────────────────────────────────────
# 전략 D: 콜드-핫 혼합
# ──────────────────────────────────────────────────

def _strategy_cold_hot(draws: list, grp: int, recent_n: int = 30) -> dict:
    """
    앞 3자리: 최근 50회 핫 자릿수 (bias=2.0)
    뒤 3자리: 전체 대비 최근 N회 콜드 자릿수 (덜 나온 쪽으로 역가중치)
    """
    hot_counters  = _build_pos_counts(draws, recent_n=50)
    all_counters  = _build_pos_counts(draws)
    cold_counters = _build_pos_counts(draws, recent_n=recent_n)

    digits = []
    for pos in range(6):
        if pos < 3:
            digits.append(_weighted_digit(hot_counters[pos], bias=2.0))
        else:
            d_list  = [str(i) for i in range(10)]
            # 전체엔 많이 나왔지만 최근엔 적게 나온 숫자 → 높은 가중치
            weights = [
                max(1, (all_counters[pos].get(d, 0) + 1) - cold_counters[pos].get(d, 0))
                for d in d_list
            ]
            digits.append(random.choices(d_list, weights=weights, k=1)[0])

    return {"grp": grp, "num": "".join(digits), "strategy": "cold_hot"}


# ──────────────────────────────────────────────────
# 공개 API
# ──────────────────────────────────────────────────

def weekly_pension_pick(draws: list, n_games: int = 5) -> list:
    """
    이번 주 연금복권 추천 n_games개.
    모든 게임은 동일한 조(grp)를 사용.

    기본 구성 (n_games=5):
      A(hot)        × 2
      B(prefix_fix) × 1
      C(sum_range)  × 1
      D(cold_hot)   × 1
    """
    if not draws:
        grp = random.randint(1, 5)
        return [
            {"grp": grp, "num": str(random.randint(0, 999999)).zfill(6), "strategy": "random"}
            for _ in range(n_games)
        ]

    grp   = _select_grp(draws)
    games = []

    hot_n = max(1, round(n_games * 0.4))
    for _ in range(hot_n):
        games.append(_strategy_hot(draws, grp))

    if len(games) < n_games:
        games.append(_strategy_prefix_fix(draws, grp))

    if len(games) < n_games:
        games.append(_strategy_sum_range(draws, grp))

    while len(games) < n_games:
        games.append(_strategy_cold_hot(draws, grp))

    return games[:n_games]


def recommend_by_digit_frequency(draws: list, games: int = 5) -> list:
    """레거시 호환 — 전략A(hot) 기반, 동일조 적용"""
    grp = _select_grp(draws)
    return [_strategy_hot(draws, grp) for _ in range(games)]


def recommend_balanced(draws: list, games: int = 5) -> list:
    """레거시 호환 — 전략C(sum_range) 기반, 동일조 적용"""
    grp = _select_grp(draws)
    return [_strategy_sum_range(draws, grp) for _ in range(games)]


def recommend_random(games: int = 5) -> list:
    """레거시 호환 — 완전 무작위 (조는 동일)"""
    grp = random.randint(1, 5)
    return [
        {"grp": grp, "num": str(random.randint(0, 999999)).zfill(6), "strategy": "random"}
        for _ in range(games)
    ]


def recommend_all_pension(draws: list, games: int = 3) -> dict:
    """
    3가지 전략 추천 결과 일괄 반환 (API용).
    각 전략 그룹은 동일한 조를 공유.
    """
    return {
        "frequency": {
            "games": recommend_by_digit_frequency(draws, games=games),
            "strategy": "frequency",
            "description": "최근 자릿수별 출현 빈도 기반, 앞자리(고등수)에 강한 가중치를 부여합니다.",
        },
        "balanced": {
            "games": recommend_balanced(draws, games=games),
            "strategy": "balanced",
            "description": "역대 당첨번호 합계 범위 내에서 통계적으로 안정된 번호를 생성합니다.",
        },
        "random": {
            "games": recommend_random(games=games),
            "strategy": "random",
            "description": "완전 무작위로 번호를 생성합니다 (동일 조 적용).",
        },
    }
