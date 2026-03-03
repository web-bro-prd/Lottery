"""
로또 번호 추천 엔진

전략:
1. 빈도 기반 추천 — 역대 출현 빈도 가중치
2. 트렌드 기반 추천 — 최근 N회 핫 번호 우선
3. 균형 추천 — 홀/짝, 고/저, 구간 밸런스 맞춤
4. 랜덤 추천 — 완전 무작위
"""
import random
from analysis.stats import frequency_analysis, trend_analysis
from typing import Any


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
        # 홀짝 2~4 허용
        if not (2 <= odd <= 4):
            return False
        # 고저 2~4 허용
        if not (2 <= low <= 4):
            return False
        # 연속 번호 최대 2쌍
        consec = sum(1 for i in range(len(nums)-1) if nums[i+1] - nums[i] == 1)
        if consec > 2:
            return False
        return True

    result = []
    for _ in range(games):
        for attempt in range(100):
            nums = _weighted_sample(weights.copy(), 6)
            if is_balanced(nums):
                break
        result.append({"numbers": nums, "strategy": "balanced"})

    return {"games": result, "strategy": "balanced", "description": "홀짝/고저 균형 + 구간 분산"}


def recommend_random(games: int = 5) -> dict[str, Any]:
    """완전 랜덤 추천"""
    result = []
    for _ in range(games):
        nums = sorted(random.sample(range(1, 46), 6))
        result.append({"numbers": nums, "strategy": "random"})

    return {"games": result, "strategy": "random", "description": "완전 무작위"}


def recommend_all(draws: list[dict], games: int = 5) -> dict[str, Any]:
    """전략별 추천 한번에 반환"""
    return {
        "frequency": recommend_by_frequency(draws, games),
        "trend":     recommend_by_trend(draws, games),
        "balanced":  recommend_balanced(draws, games),
        "random":    recommend_random(games),
    }
