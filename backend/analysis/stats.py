"""
로또 통계 분석 엔진

분석 항목:
- 번호별 출현 빈도
- 홀/짝 분포
- 고/저 분포 (1~22 저번대, 23~45 고번대)
- 번호 합계 분포
- 연속 번호 패턴
- 최근 N회차 트렌드
- 구간별 분포 (1~10, 11~20, 21~30, 31~40, 41~45)
- 번호 간격(gap) 분석
- 끝수(일의 자리) 분포
"""
from collections import Counter, defaultdict
from itertools import combinations
from typing import Any
import math


TOTAL_NUMBERS = 45


def _extract_numbers(draws: list[dict]) -> list[list[int]]:
    """회차 데이터에서 번호 리스트만 추출"""
    return [
        sorted([d["num1"], d["num2"], d["num3"], d["num4"], d["num5"], d["num6"]])
        for d in draws
    ]


def frequency_analysis(draws: list[dict]) -> dict[str, Any]:
    """
    번호별 출현 빈도 분석
    반환: {num: {count, frequency, rank}}
    """
    counter = Counter()
    for d in draws:
        for key in ["num1", "num2", "num3", "num4", "num5", "num6"]:
            counter[d[key]] += 1

    total_draws = len(draws)
    result = {}
    sorted_nums = counter.most_common()

    for rank, (num, count) in enumerate(sorted_nums, 1):
        result[num] = {
            "count": count,
            "frequency": round(count / total_draws * 100, 2) if total_draws else 0,
            "rank": rank,
        }

    # 출현 0인 번호 채우기
    for n in range(1, TOTAL_NUMBERS + 1):
        if n not in result:
            result[n] = {"count": 0, "frequency": 0.0, "rank": TOTAL_NUMBERS}

    return result


def bonus_frequency(draws: list[dict]) -> dict[int, dict]:
    """보너스 번호 빈도"""
    counter = Counter(d["bonus"] for d in draws)
    total = len(draws)
    result = {}
    for n in range(1, TOTAL_NUMBERS + 1):
        cnt = counter.get(n, 0)
        result[n] = {
            "count": cnt,
            "frequency": round(cnt / total * 100, 2) if total else 0,
        }
    return result


def odd_even_distribution(draws: list[dict]) -> dict[str, Any]:
    """
    홀/짝 분포 분석
    반환: {pattern: count} — e.g. "3홀3짝": 120
    """
    pattern_counter = Counter()
    for nums in _extract_numbers(draws):
        odd = sum(1 for n in nums if n % 2 == 1)
        even = 6 - odd
        pattern_counter[f"{odd}홀{even}짝"] += 1

    total = len(draws)
    return {
        "patterns": {
            p: {"count": c, "frequency": round(c / total * 100, 2)}
            for p, c in sorted(pattern_counter.items(), key=lambda x: -x[1])
        }
    }


def high_low_distribution(draws: list[dict]) -> dict[str, Any]:
    """
    고/저 번호 분포 (저: 1~22, 고: 23~45)
    """
    pattern_counter = Counter()
    for nums in _extract_numbers(draws):
        low = sum(1 for n in nums if n <= 22)
        high = 6 - low
        pattern_counter[f"{low}저{high}고"] += 1

    total = len(draws)
    return {
        "patterns": {
            p: {"count": c, "frequency": round(c / total * 100, 2)}
            for p, c in sorted(pattern_counter.items(), key=lambda x: -x[1])
        }
    }


def sum_distribution(draws: list[dict]) -> dict[str, Any]:
    """
    번호 합계 분포
    이론적 최소: 21 (1+2+3+4+5+6), 최대: 255 (40+41+42+43+44+45)
    """
    sums = [sum(nums) for nums in _extract_numbers(draws)]
    counter = Counter(sums)

    avg = sum(sums) / len(sums) if sums else 0
    # 구간별 집계 (10 단위)
    buckets = defaultdict(int)
    for s in sums:
        bucket = (s // 20) * 20
        buckets[f"{bucket}~{bucket+19}"] += 1

    total = len(draws)
    return {
        "average": round(avg, 1),
        "min": min(sums) if sums else 0,
        "max": max(sums) if sums else 0,
        "buckets": {
            k: {"count": v, "frequency": round(v / total * 100, 2)}
            for k, v in sorted(buckets.items())
        },
        "raw": dict(sorted(counter.items())),
    }


def consecutive_analysis(draws: list[dict]) -> dict[str, Any]:
    """연속 번호 패턴 분석"""
    pattern_counter = Counter()
    for nums in _extract_numbers(draws):
        consecutive = 0
        for i in range(len(nums) - 1):
            if nums[i + 1] - nums[i] == 1:
                consecutive += 1
        pattern_counter[consecutive] += 1

    total = len(draws)
    return {
        "patterns": {
            f"연속{k}쌍": {"count": v, "frequency": round(v / total * 100, 2)}
            for k, v in sorted(pattern_counter.items())
        }
    }


def zone_distribution(draws: list[dict]) -> dict[str, Any]:
    """
    구간별 분포 분석
    구간: 1~9, 10~19, 20~29, 30~39, 40~45
    """
    zones = {
        "1~9": range(1, 10),
        "10~19": range(10, 20),
        "20~29": range(20, 30),
        "30~39": range(30, 40),
        "40~45": range(40, 46),
    }

    # 회차별 구간 패턴
    pattern_counter = Counter()
    zone_totals = defaultdict(int)

    for nums in _extract_numbers(draws):
        zone_counts = []
        for zone_name, zone_range in zones.items():
            cnt = sum(1 for n in nums if n in zone_range)
            zone_totals[zone_name] += cnt
            zone_counts.append(str(cnt))
        pattern_counter["-".join(zone_counts)] += 1

    total_draws = len(draws)
    total_nums = total_draws * 6

    return {
        "zone_frequency": {
            zone: {
                "total": cnt,
                "avg_per_draw": round(cnt / total_draws, 2) if total_draws else 0,
                "share": round(cnt / total_nums * 100, 2) if total_nums else 0,
            }
            for zone, cnt in zone_totals.items()
        },
        "top_patterns": [
            {"pattern": p, "count": c, "frequency": round(c / total_draws * 100, 2)}
            for p, c in pattern_counter.most_common(10)
        ],
    }


def last_digit_distribution(draws: list[dict]) -> dict[str, Any]:
    """끝수(일의 자리) 분포"""
    counter = Counter()
    for nums in _extract_numbers(draws):
        for n in nums:
            counter[n % 10] += 1

    total = len(draws) * 6
    return {
        str(d): {"count": counter.get(d, 0), "frequency": round(counter.get(d, 0) / total * 100, 2)}
        for d in range(10)
    }


def pair_frequency(draws: list[dict], top_n: int = 20) -> list[dict]:
    """자주 함께 나오는 번호 쌍 분석"""
    pair_counter = Counter()
    for nums in _extract_numbers(draws):
        for a, b in combinations(nums, 2):
            pair_counter[(a, b)] += 1

    total = len(draws)
    return [
        {
            "pair": list(pair),
            "count": count,
            "frequency": round(count / total * 100, 2),
        }
        for pair, count in pair_counter.most_common(top_n)
    ]


def triple_frequency(draws: list[dict], top_n: int = 10) -> list[dict]:
    """자주 함께 나오는 번호 3개 조합"""
    triple_counter = Counter()
    for nums in _extract_numbers(draws):
        for combo in combinations(nums, 3):
            triple_counter[combo] += 1

    total = len(draws)
    return [
        {
            "triple": list(t),
            "count": count,
            "frequency": round(count / total * 100, 2),
        }
        for t, count in triple_counter.most_common(top_n)
    ]


def trend_analysis(draws: list[dict], recent_n: int = 50) -> dict[str, Any]:
    """
    최근 N회 트렌드 분석
    - 최근 N회 핫 번호 vs 전체 평균 대비 출현율
    """
    if len(draws) < recent_n:
        recent_n = len(draws)

    recent = draws[-recent_n:]
    all_freq = frequency_analysis(draws)
    recent_freq = frequency_analysis(recent)

    hot = []
    cold = []
    for n in range(1, TOTAL_NUMBERS + 1):
        all_f = all_freq[n]["frequency"]
        recent_f = recent_freq[n]["frequency"]
        diff = recent_f - all_f
        entry = {
            "number": n,
            "all_frequency": all_f,
            "recent_frequency": recent_f,
            "diff": round(diff, 2),
        }
        if diff > 0:
            hot.append(entry)
        else:
            cold.append(entry)

    hot.sort(key=lambda x: -x["diff"])
    cold.sort(key=lambda x: x["diff"])

    return {
        "recent_n": recent_n,
        "hot_numbers": hot[:10],
        "cold_numbers": cold[:10],
    }


def get_full_stats(draws: list[dict]) -> dict[str, Any]:
    """전체 통계 한번에 반환"""
    if not draws:
        return {}

    return {
        "total_draws": len(draws),
        "latest_round": draws[-1]["round"] if draws else 0,
        "frequency": frequency_analysis(draws),
        "bonus_frequency": bonus_frequency(draws),
        "odd_even": odd_even_distribution(draws),
        "high_low": high_low_distribution(draws),
        "sum_dist": sum_distribution(draws),
        "consecutive": consecutive_analysis(draws),
        "zone": zone_distribution(draws),
        "last_digit": last_digit_distribution(draws),
        "pair_frequency": pair_frequency(draws, top_n=20),
        "triple_frequency": triple_frequency(draws, top_n=10),
        "trend": trend_analysis(draws, recent_n=50),
    }
