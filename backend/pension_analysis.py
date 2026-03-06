"""
연금복권720+ 분석 엔진
- 자릿수별 0~9 빈도 분석
- 조(1~5) 출현 분포
- 핫/콜드 자릿수 분석
- 홀짝 분포
- 시뮬레이션 (랜덤 구매 ROI)
"""
import random
from collections import Counter


# ──────────────────────────────────────────────────
# 기본 통계
# ──────────────────────────────────────────────────

def digit_frequency(draws: list) -> dict:
    """
    자릿수별(1~6번째) 0~9 출현 빈도 분석
    반환: {
      "d1": {"0": {"count":5, "pct":1.64}, ...},
      "d2": {...},
      ...
      "d6": {...}
    }
    """
    total = len(draws)
    if total == 0:
        return {}

    result = {}
    for pos in range(6):
        key = f"d{pos+1}"
        counts = Counter()
        for draw in draws:
            num = str(draw["num"]).zfill(6)
            counts[num[pos]] += 1
        result[key] = {
            digit: {
                "count": counts.get(digit, 0),
                "pct": round(counts.get(digit, 0) / total * 100, 2),
            }
            for digit in [str(i) for i in range(10)]
        }
    return result


def group_distribution(draws: list) -> dict:
    """
    조(1~5) 출현 분포
    반환: {"1": {"count":61,"pct":20.0}, ...}
    """
    total = len(draws)
    if total == 0:
        return {}
    counts = Counter(str(d["grp"]) for d in draws)
    return {
        str(g): {
            "count": counts.get(str(g), 0),
            "pct": round(counts.get(str(g), 0) / total * 100, 2),
        }
        for g in range(1, 6)
    }


def hot_cold_digits(draws: list, recent_n: int = 30) -> dict:
    """
    최근 N회와 전체 비교하여 핫/콜드 자릿수 반환
    반환: {
      "d1": {"hot": ["3","7",...], "cold": ["0","9",...]},
      ...
    }
    """
    if not draws:
        return {}

    recent = draws[-recent_n:] if len(draws) >= recent_n else draws
    recent_freq = digit_frequency(recent)
    all_freq = digit_frequency(draws)

    result = {}
    for pos in range(6):
        key = f"d{pos+1}"
        diffs = []
        for digit in [str(i) for i in range(10)]:
            r_pct = recent_freq.get(key, {}).get(digit, {}).get("pct", 0.0)
            a_pct = all_freq.get(key, {}).get(digit, {}).get("pct", 0.0)
            diffs.append((digit, r_pct - a_pct, r_pct, a_pct))
        diffs.sort(key=lambda x: x[1], reverse=True)
        result[key] = {
            "hot":  [{"digit": d[0], "recent_pct": d[2], "all_pct": d[3], "diff": round(d[1], 2)} for d in diffs[:3]],
            "cold": [{"digit": d[0], "recent_pct": d[2], "all_pct": d[3], "diff": round(d[1], 2)} for d in diffs[-3:]],
        }
    return result


def odd_even_distribution(draws: list) -> dict:
    """
    6자리 번호 전체의 홀짝 분포 (숫자 기준)
    반환: {"odd_pct": 45.2, "even_pct": 54.8}
    """
    if not draws:
        return {}
    odd_total = 0
    even_total = 0
    for draw in draws:
        for ch in str(draw["num"]).zfill(6):
            if int(ch) % 2 == 1:
                odd_total += 1
            else:
                even_total += 1
    total = odd_total + even_total
    return {
        "odd_count": odd_total,
        "even_count": even_total,
        "odd_pct": round(odd_total / total * 100, 2),
        "even_pct": round(even_total / total * 100, 2),
    }


def num_sum_distribution(draws: list) -> dict:
    """
    6자리 번호의 각 자리 합계 분포
    """
    if not draws:
        return {}
    sums = [sum(int(c) for c in str(d["num"]).zfill(6)) for d in draws]
    total = len(sums)
    counts = Counter(sums)
    return {
        "average": round(sum(sums) / total, 2),
        "min": min(sums),
        "max": max(sums),
        "distribution": {
            str(k): {"count": v, "pct": round(v / total * 100, 2)}
            for k, v in sorted(counts.items())
        },
    }


def get_full_pension_stats(draws: list) -> dict:
    """전체 통계 반환"""
    if not draws:
        return {}
    latest = draws[-1]
    return {
        "total_draws":       len(draws),
        "latest_round":      latest["round"],
        "latest_date":       latest["draw_date"],
        "digit_frequency":   digit_frequency(draws),
        "group_distribution": group_distribution(draws),
        "hot_cold":          hot_cold_digits(draws, recent_n=30),
        "odd_even":          odd_even_distribution(draws),
        "sum_distribution":  num_sum_distribution(draws),
    }


# ──────────────────────────────────────────────────
# 등수 판별
# ──────────────────────────────────────────────────

def check_pension_rank(
    my_grp: int, my_num: str,
    win_grp: int, win_num: str,
    bonus_num: str = "",
) -> int:
    """
    연금복권720+ 등수 판별
    1등: 조 일치 + 6자리 모두 일치
    2등: 조 불일치 + 6자리 모두 일치
    3등: 앞 5자리 일치 (끝 1자리 다름)
    4등: 앞 4자리 일치
    5등: 앞 3자리 일치
    6등: 앞 2자리 일치
    7등: 끝 1자리 일치
    0: 낙첨
    """
    m = str(my_num).zfill(6)
    w = str(win_num).zfill(6)

    if m == w:
        if my_grp == win_grp:
            return 1
        return 2

    # 앞자리 일치 체크
    for i in range(5, 0, -1):
        if m[:i] == w[:i]:
            return 8 - i  # 5→3등, 4→4등, 3→5등, 2→6등

    # 끝자리 일치
    if m[-1] == w[-1]:
        return 7

    return 0


# ──────────────────────────────────────────────────
# 시뮬레이션
# ──────────────────────────────────────────────────

PENSION_PRIZE = {
    1: 7_000_000 * 12 * 20,  # 월 700만원×20년 환산 (일시금 기준 약 16.8억)
    2: 700_000 * 12 * 10,    # 월 70만원×10년 환산
    3: 10_000_000,
    4: 1_000_000,
    5: 100_000,
    6: 10_000,
    7: 5_000,
    0: 0,
}

TICKET_PRICE = 1_000  # 1장 1,000원


def simulate_pension_random(draws: list, games_per_round: int = 5) -> dict:
    """
    랜덤 구매 시뮬레이션
    각 회차마다 games_per_round 게임을 무작위로 구매
    """
    if not draws:
        return {}

    total_spent = 0
    total_prize = 0
    rank_counts: dict = {str(r): 0 for r in range(8)}
    detail = []

    for draw in draws:
        win_grp = draw["grp"]
        win_num = str(draw["num"]).zfill(6)
        spent = games_per_round * TICKET_PRICE
        prize = 0

        for _ in range(games_per_round):
            my_grp = random.randint(1, 5)
            my_num = str(random.randint(0, 999999)).zfill(6)
            rank = check_pension_rank(my_grp, my_num, win_grp, win_num)
            prize += PENSION_PRIZE.get(rank, 0)
            rank_counts[str(rank)] = rank_counts.get(str(rank), 0) + 1

        total_spent += spent
        total_prize += prize
        detail.append({
            "round": draw["round"],
            "spent": spent,
            "prize": prize,
        })

    net = total_prize - total_spent
    roi = round(total_prize / total_spent * 100, 2) if total_spent else 0.0

    return {
        "rounds_played":    len(draws),
        "games_per_round":  games_per_round,
        "total_spent":      total_spent,
        "total_prize":      total_prize,
        "net":              net,
        "roi":              roi,
        "rank_counts":      rank_counts,
        "detail":           detail[-20:],  # 최근 20회만 반환
    }
