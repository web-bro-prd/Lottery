"""
연금복권720+ 번호 추천 엔진 v4

설계 원칙:
  - 조(1~5)는 과거 빈도로 예측하지 않는다. 이론적으로 균등하므로 무작위 선택한다.
  - 번호는 최근/전체 자릿수 분포를 함께 반영하되, 최근 당첨번호를 과도하게 따라가지 않는다.
  - 최근 당첨번호와 지나치게 같은 prefix를 갖는 후보, 최근 번호와 완전히 같은 후보는 감점한다.
  - weekly 추천은 여러 전략 후보를 만든 뒤 점수화해서 최선 1개를 선택한다.
"""
import random
import statistics
from collections import Counter
from typing import Optional


def _build_pos_counts(draws: list, recent_n: Optional[int] = None) -> list[Counter]:
    src = draws[-recent_n:] if recent_n and len(draws) >= recent_n else draws
    counters = [Counter() for _ in range(6)]
    for draw in src:
        num = str(draw["num"]).zfill(6)
        for pos, ch in enumerate(num):
            counters[pos][ch] += 1
    return counters


def _blend_weight(
    all_counter: Counter,
    recent_counter: Counter,
    digit: str,
    total_all: int,
    total_recent: int,
    recent_weight: float = 0.6,
) -> float:
    all_rate = (all_counter.get(digit, 0) + 1) / (total_all + 10)
    recent_rate = (recent_counter.get(digit, 0) + 1) / (total_recent + 10)
    return (1.0 - recent_weight) * all_rate + recent_weight * recent_rate


def _weighted_digit_blended(
    all_counter: Counter,
    recent_counter: Counter,
    total_all: int,
    total_recent: int,
    recent_weight: float = 0.6,
    temperature: float = 1.0,
) -> str:
    digits = [str(i) for i in range(10)]
    weights = [
        _blend_weight(all_counter, recent_counter, d, total_all, total_recent, recent_weight) ** temperature
        for d in digits
    ]
    return random.choices(digits, weights=weights, k=1)[0]


def _uniform_grp() -> int:
    """조는 과거 빈도로 우열이 없으므로 균등 무작위 선택."""
    return random.randint(1, 5)


def _recent_prefix_match_len(num: str, draws: list, recent_n: int = 12) -> int:
    refs = [str(d["num"]).zfill(6) for d in draws[-recent_n:]]
    best = 0
    for ref in refs:
        cur = 0
        for i in range(6):
            if num[i] != ref[i]:
                break
            cur += 1
        best = max(best, cur)
    return best


def _repeat_digit_penalty(num: str) -> float:
    cnt = Counter(num)
    max_dup = max(cnt.values())
    if max_dup >= 4:
        return 10.0
    if max_dup == 3:
        return 4.0
    return 0.0


def _unique_digit_score(num: str) -> float:
    unique_n = len(set(num))
    if unique_n >= 5:
        return 8.0
    if unique_n == 4:
        return 5.0
    if unique_n == 3:
        return 1.5
    return 0.0


def _odd_even_balance_score(num: str) -> float:
    odd = sum(int(ch) % 2 for ch in num)
    if 2 <= odd <= 4:
        return 6.0
    if odd in (1, 5):
        return 2.0
    return 0.0


def _sum_score(num: str, avg_sum: float, std_sum: float) -> float:
    num_sum = sum(int(c) for c in num)
    if std_sum <= 0:
        return 14.0
    z = abs(num_sum - avg_sum) / std_sum
    return max(0.0, 14.0 * (1 - z / 2.2))


def _position_score(num: str, all_counts: list[Counter], recent_counts: list[Counter], total_all: int, total_recent: int) -> float:
    score = 0.0
    for pos, ch in enumerate(num):
        rate = _blend_weight(
            all_counts[pos],
            recent_counts[pos],
            ch,
            total_all=total_all,
            total_recent=total_recent,
            recent_weight=0.58 if pos < 3 else 0.48,
        )
        weight = 1.25 if pos < 3 else 1.0
        score += rate * weight
    return (score / 6.75) * 48.0


def _recent_duplicate_penalty(num: str, draws: list) -> float:
    recent_nums = {str(d["num"]).zfill(6) for d in draws[-30:]}
    if num in recent_nums:
        return 20.0
    prefix_len = _recent_prefix_match_len(num, draws, recent_n=12)
    if prefix_len >= 5:
        return 14.0
    if prefix_len == 4:
        return 8.0
    if prefix_len == 3:
        return 3.0
    return 0.0


def _gen_blended(draws: list, grp: int, recent_n: int = 60) -> dict:
    all_counts = _build_pos_counts(draws)
    recent_counts = _build_pos_counts(draws, recent_n=recent_n)
    total_all = max(1, len(draws))
    total_recent = max(1, min(recent_n, len(draws)))
    digits = [
        _weighted_digit_blended(
            all_counts[pos],
            recent_counts[pos],
            total_all=total_all,
            total_recent=total_recent,
            recent_weight=0.62 if pos < 3 else 0.50,
            temperature=1.08 if pos < 2 else 1.0,
        )
        for pos in range(6)
    ]
    return {"grp": grp, "num": "".join(digits), "strategy": "frequency"}


def _gen_balanced(draws: list, grp: int) -> dict:
    if not draws:
        return {"grp": grp, "num": str(random.randint(0, 999999)).zfill(6), "strategy": "balanced"}

    all_counts = _build_pos_counts(draws)
    recent_counts = _build_pos_counts(draws, recent_n=80)
    total_all = max(1, len(draws))
    total_recent = max(1, min(80, len(draws)))
    sums = [sum(int(c) for c in str(d["num"]).zfill(6)) for d in draws]
    avg_sum = statistics.mean(sums)
    std_sum = statistics.stdev(sums) if len(sums) > 1 else 5.0

    best_num = None
    best_gap = 1e9
    for _ in range(240):
        digits = [
            _weighted_digit_blended(
                all_counts[pos],
                recent_counts[pos],
                total_all=total_all,
                total_recent=total_recent,
                recent_weight=0.52,
                temperature=0.95,
            )
            for pos in range(6)
        ]
        num = "".join(digits)
        total = sum(int(c) for c in num)
        if len(set(num)) < 4:
            continue
        if _recent_prefix_match_len(num, draws, recent_n=10) >= 4:
            continue
        gap = abs(total - avg_sum)
        if gap < best_gap and gap <= std_sum * 0.9:
            best_num = num
            best_gap = gap
            if gap <= 1:
                break

    if best_num is None:
        best_num = _gen_blended(draws, grp)["num"]
    return {"grp": grp, "num": best_num, "strategy": "balanced"}


def _gen_diverse(draws: list, grp: int) -> dict:
    if not draws:
        return {"grp": grp, "num": str(random.randint(0, 999999)).zfill(6), "strategy": "diverse"}

    all_counts = _build_pos_counts(draws)
    recent_counts = _build_pos_counts(draws, recent_n=40)
    total_all = max(1, len(draws))
    total_recent = max(1, min(40, len(draws)))

    for _ in range(200):
        digits = [
            _weighted_digit_blended(
                all_counts[pos],
                recent_counts[pos],
                total_all=total_all,
                total_recent=total_recent,
                recent_weight=0.45,
                temperature=1.15,
            )
            for pos in range(6)
        ]
        num = "".join(digits)
        if len(set(num)) < 5:
            continue
        if _recent_prefix_match_len(num, draws, recent_n=12) >= 4:
            continue
        return {"grp": grp, "num": num, "strategy": "diverse"}

    return {"grp": grp, "num": _gen_blended(draws, grp)["num"], "strategy": "diverse"}


def _score(candidate: dict, draws: list, all_counts: list[Counter], recent_counts: list[Counter], avg_sum: float, std_sum: float) -> float:
    num = str(candidate["num"]).zfill(6)
    if not draws:
        return 0.0

    total_all = max(1, len(draws))
    total_recent = max(1, min(60, len(draws)))

    score = 0.0
    score += _position_score(num, all_counts, recent_counts, total_all, total_recent)
    score += _sum_score(num, avg_sum, std_sum)
    score += _unique_digit_score(num)
    score += _odd_even_balance_score(num)

    penalty = 0.0
    penalty += _repeat_digit_penalty(num)
    penalty += _recent_duplicate_penalty(num, draws)

    final = max(0.0, score - penalty)
    return round(final, 2)


def _rationale(candidate: dict, draws: list, avg_sum: float) -> list[str]:
    num = str(candidate["num"]).zfill(6)
    prefix_len = _recent_prefix_match_len(num, draws, recent_n=12)
    parts = [
        f"합계 {sum(int(c) for c in num)} (평균 {avg_sum:.1f} 근처)",
        f"고유 숫자 {len(set(num))}개",
        f"최근 당첨번호 최대 앞자리 일치 {prefix_len}자리",
    ]
    return parts


def weekly_pension_pick(draws: list) -> dict:
    """
    이번 주 연금복권 최적 추천 1개 반환.
    조는 균등 무작위, 번호는 최근/전체 혼합 분포와 과도한 최근 추종 억제를 함께 반영한다.
    """
    grp = _uniform_grp()
    if not draws:
        return {
            "grp": grp,
            "num": str(random.randint(0, 999999)).zfill(6),
            "strategy": "random",
            "score": 0.0,
            "rationale": ["데이터 부족으로 무작위 생성"],
        }

    all_counts = _build_pos_counts(draws)
    recent_counts = _build_pos_counts(draws, recent_n=60)
    sums = [sum(int(c) for c in str(d["num"]).zfill(6)) for d in draws]
    avg_sum = statistics.mean(sums)
    std_sum = statistics.stdev(sums) if len(sums) > 1 else 5.0

    candidates = []
    for _ in range(12):
        candidates.append(_gen_blended(draws, grp))
        candidates.append(_gen_balanced(draws, grp))
        candidates.append(_gen_diverse(draws, grp))
    for _ in range(6):
        candidates.append({"grp": grp, "num": str(random.randint(0, 999999)).zfill(6), "strategy": "random"})

    dedup = {}
    for c in candidates:
        dedup[c["num"]] = c
    scored = [
        {**c, "score": _score(c, draws, all_counts, recent_counts, avg_sum, std_sum)}
        for c in dedup.values()
    ]
    best = max(scored, key=lambda x: x["score"])
    best["rationale"] = _rationale(best, draws, avg_sum)
    return best


def recommend_all_pension(draws: list, games: int = 3) -> dict:
    """
    API용: 전략별 번호 추천.
    조는 역사적 우위가 없다고 보고 각 게임마다 균등 무작위 선택한다.
    """
    def _make_games(gen_fn, n: int) -> list[dict]:
        result = []
        for _ in range(n):
            grp = _uniform_grp()
            result.append(gen_fn(draws, grp))
        return result

    freq_games = _make_games(_gen_blended, games)
    bal_games = _make_games(_gen_balanced, games)
    rand_games = [
        {"grp": _uniform_grp(), "num": str(random.randint(0, 999999)).zfill(6), "strategy": "random"}
        for _ in range(games)
    ]

    return {
        "frequency": {
            "games": freq_games,
            "strategy": "frequency",
            "description": "최근/전체 자릿수 빈도를 함께 반영한 혼합 분포 기반 추천입니다.",
        },
        "balanced": {
            "games": bal_games,
            "strategy": "balanced",
            "description": "합계와 숫자 중복도를 안정 범위로 맞추고 최근 당첨번호와 과도한 유사성을 줄인 추천입니다.",
        },
        "random": {
            "games": rand_games,
            "strategy": "random",
            "description": "비교용 무작위 추천입니다.",
        },
    }


def recommend_by_digit_frequency(draws: list, games: int = 5) -> list:
    return [_gen_blended(draws, _uniform_grp()) for _ in range(games)]


def recommend_balanced(draws: list, games: int = 5) -> list:
    return [_gen_balanced(draws, _uniform_grp()) for _ in range(games)]


def recommend_random(games: int = 5) -> list:
    return [
        {"grp": _uniform_grp(), "num": str(random.randint(0, 999999)).zfill(6), "strategy": "random"}
        for _ in range(games)
    ]
