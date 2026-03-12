"""
로또 번호 추천 엔진

전략:
0. 스마트 추천   — 백테스트 기반 조건 예측 + 다양성 리랭킹
1. 빈도 기반 추천 — 역대 출현 빈도 가중치
2. 트렌드 기반 추천 — 최근 N회 핫 번호 우선
3. 균형 추천 — 홀/짝, 고/저, 구간 밸런스 맞춤
4. 랜덤 추천 — 완전 무작위
"""
import random
from analysis.stats import frequency_analysis, trend_analysis
from analysis.backtest import generate_recommendations, _ac_value
from typing import Any


def _zone_index(n: int) -> int:
    if n <= 9:
        return 0
    if n <= 19:
        return 1
    if n <= 29:
        return 2
    if n <= 39:
        return 3
    return 4


def _overlap_count(a: list[int], b: list[int]) -> int:
    return len(set(a) & set(b))


def _select_diverse_games(
    candidates: list[tuple[float, list[int]]],
    games: int,
    max_overlap: int = 3,
) -> list[list[int]]:
    """점수 상위 후보에서 과도하게 비슷한 조합을 줄이며 선택."""
    selected: list[list[int]] = []

    for _, nums in candidates:
        if all(_overlap_count(nums, picked) <= max_overlap for picked in selected):
            selected.append(nums)
        if len(selected) >= games:
            return selected

    for _, nums in candidates:
        if nums not in selected:
            selected.append(nums)
        if len(selected) >= games:
            break

    return selected


def _weighted_sample(weights: dict[int, float], k: int) -> list[int]:
    """
    가중치 기반 비복원 추출
    weights: {num: weight}
    """
    nums = list(weights.keys())
    wts = [weights[n] for n in nums]

    selected = []
    for _ in range(k):
        total = sum(wts)
        r = random.uniform(0, total)
        cumulative = 0
        for i, w in enumerate(wts):
            cumulative += w
            if r <= cumulative:
                selected.append(nums[i])
                # 선택된 번호 제거
                nums.pop(i)
                wts.pop(i)
                break

    return sorted(selected)


def recommend_by_frequency(draws: list[dict], games: int = 5) -> dict[str, Any]:
    """
    빈도 기반 번호 추천
    출현 빈도가 높은 번호에 높은 가중치
    """
    if not draws:
        return {"games": []}

    freq = frequency_analysis(draws)
    weights = {n: max(info["count"], 0.1) for n, info in freq.items()}

    result = []
    for _ in range(games):
        nums = _weighted_sample(weights.copy(), 6)
        result.append({"numbers": nums, "strategy": "frequency"})

    return {"games": result, "strategy": "frequency", "description": "역대 출현 빈도 가중치 기반"}


def recommend_by_trend(draws: list[dict], games: int = 5, recent_n: int = 50) -> dict[str, Any]:
    """
    트렌드 기반 번호 추천
    최근 N회에서 상대적으로 자주 나온 번호 우선
    """
    if not draws:
        return {"games": []}

    trend = trend_analysis(draws, recent_n=recent_n)
    freq = frequency_analysis(draws)

    # 최근 빈도와 전체 빈도 혼합 (최근 70%, 전체 30%)
    weights = {}
    for n in range(1, 46):
        all_f = freq[n]["frequency"]
        # trend 데이터에서 recent_frequency 찾기
        recent_f = all_f
        for item in trend.get("hot_numbers", []) + trend.get("cold_numbers", []):
            if item["number"] == n:
                recent_f = item["recent_frequency"]
                break
        weights[n] = max(recent_f * 0.7 + all_f * 0.3, 0.1)

    result = []
    for _ in range(games):
        nums = _weighted_sample(weights.copy(), 6)
        result.append({"numbers": nums, "strategy": "trend"})

    return {"games": result, "strategy": "trend", "description": f"최근 {recent_n}회 트렌드 기반"}


def recommend_smart(draws: list[dict], games: int = 5, recent_n: int = 50) -> dict[str, Any]:
    """
    스마트 추천
    - 백테스트에서 성능이 좋았던 WEIGHTED_RECENT 조건 예측 사용
    - 상위 후보를 많이 생성한 뒤, 번호 겹침이 과한 조합은 줄여 다양성 확보
    - 최근 트렌드/역대 빈도를 소폭 반영해 극단적인 후보를 완화
    """
    if len(draws) < 120:
        fallback = recommend_balanced(draws, games)
        return {
            "games": [{"numbers": g["numbers"], "strategy": "smart"} for g in fallback["games"]],
            "strategy": "smart",
            "description": "데이터가 적어 균형 추천 기준으로 대체한 스마트 추천",
        }

    window = min(600, max(180, len(draws) // 2), len(draws) - 1)
    candidate_count = max(games * 8, 40)
    rec = generate_recommendations(
        draws,
        method="WEIGHTED_RECENT",
        window=window,
        n_games=candidate_count,
    )

    freq = frequency_analysis(draws)
    trend = trend_analysis(draws, recent_n=min(recent_n, len(draws)))
    recent_freq_map = {n: freq[n]["frequency"] for n in range(1, 46)}
    for item in trend.get("hot_numbers", []) + trend.get("cold_numbers", []):
        recent_freq_map[item["number"]] = item["recent_frequency"]

    scored_candidates: list[tuple[float, list[int]]] = []
    for base_score, nums in zip(rec.get("scores", []), rec.get("games", [])):
        avg_hist = sum(freq[n]["frequency"] for n in nums) / 6
        avg_recent = sum(recent_freq_map[n] for n in nums) / 6
        spread_bonus = 0.03 if _ac_value(nums) >= 6 else 0.0
        adjusted = float(base_score) + avg_hist * 0.25 + avg_recent * 0.35 + spread_bonus
        scored_candidates.append((adjusted, nums))

    scored_candidates.sort(key=lambda item: -item[0])
    picked = _select_diverse_games(scored_candidates, games, max_overlap=2)

    result = [{"numbers": nums, "strategy": "smart"} for nums in picked]
    return {
        "games": result,
        "strategy": "smart",
        "description": f"백테스트 기반 조건 예측(WEIGHTED_RECENT, window={window}) 후 다양성 리랭킹",
    }


def recommend_balanced(draws: list[dict], games: int = 5) -> dict[str, Any]:
    """
    균형 추천
    - 홀짝 3:3 또는 2:4
    - 저고 3:3 또는 2:4
    - 구간(1~9, 10~19, 20~29, 30~39, 40~45)에서 최소 1개
    - 연속 번호 최대 2쌍
    """
    freq = frequency_analysis(draws) if draws else {n: {"count": 1} for n in range(1, 46)}
    weights = {n: max(freq[n]["count"], 0.1) for n in range(1, 46)}

    def is_balanced(nums: list[int]) -> bool:
        odd = sum(1 for n in nums if n % 2 == 1)
        low = sum(1 for n in nums if n <= 22)
        zone_counts = {}
        for n in nums:
            z = _zone_index(n)
            zone_counts[z] = zone_counts.get(z, 0) + 1
        # 홀짝 2~4 허용
        if not (2 <= odd <= 4):
            return False
        # 고저 2~4 허용
        if not (2 <= low <= 4):
            return False
        # 구간 분산: 최소 4개 구간 사용, 특정 구간 쏠림 최대 2개
        if len(zone_counts) < 4 or max(zone_counts.values()) > 2:
            return False
        # 연속 번호 최대 2쌍
        consec = sum(1 for i in range(len(nums)-1) if nums[i+1] - nums[i] == 1)
        if consec > 2:
            return False
        # 지나치게 좁은/넓은 조합 방지
        total = sum(nums)
        if not (100 <= total <= 179):
            return False
        return True

    result = []
    for _ in range(games):
        nums = None
        for attempt in range(100):
            nums = _weighted_sample(weights.copy(), 6)
            if is_balanced(nums):
                break
        if nums is None:
            nums = _weighted_sample(weights.copy(), 6)
        result.append({"numbers": nums, "strategy": "balanced"})

    return {"games": result, "strategy": "balanced", "description": "홀짝/고저 균형 + 구간 분산"}


def recommend_random(games: int = 5) -> dict[str, Any]:
    """완전 랜덤 추천"""
    result = []
    for _ in range(games):
        nums = sorted(random.sample(range(1, 46), 6))
        result.append({"numbers": nums, "strategy": "random"})

    return {"games": result, "strategy": "random", "description": "완전 무작위"}


def recommend_all(draws: list[dict], games: int = 5, recent_n: int = 50) -> dict[str, Any]:
    """전략별 추천 한번에 반환"""
    return {
        "smart":     recommend_smart(draws, games, recent_n=recent_n),
        "frequency": recommend_by_frequency(draws, games),
        "trend":     recommend_by_trend(draws, games, recent_n=recent_n),
        "balanced":  recommend_balanced(draws, games),
        "random":    recommend_random(games),
    }
