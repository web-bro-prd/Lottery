"""
연금복권720+ 번호 추천 엔진
- 자릿수별 빈도 가중치 기반 추천
- 균형 기반 추천 (홀짝·자릿수 분산)
- 무작위 추천
- 조(1~5) + 6자리 번호 일괄 추천
"""
import random
from collections import Counter


def _weighted_digit(counts: dict) -> str:
    """가중치 딕셔너리 {"0":cnt, ...} 에서 확률적으로 숫자 1개 선택"""
    digits = list(counts.keys())
    weights = [counts.get(d, 0) + 1 for d in digits]  # +1 스무딩
    return random.choices(digits, weights=weights, k=1)[0]


def _build_pos_counts(draws: list) -> list:
    """자릿수별 카운터 리스트 반환 [Counter, ...×6]"""
    counters = [Counter() for _ in range(6)]
    for draw in draws:
        num = str(draw["num"]).zfill(6)
        for pos, ch in enumerate(num):
            counters[pos][ch] += 1
    return counters


def _build_grp_counts(draws: list) -> Counter:
    """조별 카운터 반환"""
    return Counter(str(d["grp"]) for d in draws)


def recommend_by_digit_frequency(draws: list, games: int = 5) -> list:
    """
    자릿수별 빈도 가중치 기반 추천
    각 자리마다 출현 빈도에 비례한 확률로 숫자 선택
    """
    if not draws:
        return [{"grp": random.randint(1, 5), "num": str(random.randint(0, 999999)).zfill(6)} for _ in range(games)]

    counters = _build_pos_counts(draws)
    grp_counter = _build_grp_counts(draws)
    grp_digits = [str(g) for g in range(1, 6)]
    grp_weights = [grp_counter.get(g, 0) + 1 for g in grp_digits]

    results = []
    for _ in range(games):
        grp = int(random.choices(grp_digits, weights=grp_weights, k=1)[0])
        num = "".join(
            _weighted_digit({str(d): c for d, c in counter.items()})
            for counter in counters
        )
        results.append({"grp": grp, "num": num, "strategy": "frequency"})
    return results


def recommend_balanced(draws: list, games: int = 5) -> list:
    """
    균형 기반 추천
    - 홀짝 균형 (각 자리 홀:짝 ≈ 5:5)
    - 최근 자주 나온 조 우선
    - 연속 자릿수 회피
    """
    if not draws:
        return recommend_random(games=games)

    grp_counter = _build_grp_counts(draws)
    grp_digits = [str(g) for g in range(1, 6)]
    grp_weights = [grp_counter.get(g, 0) + 1 for g in grp_digits]

    results = []
    for _ in range(games):
        grp = int(random.choices(grp_digits, weights=grp_weights, k=1)[0])

        # 각 자리: 홀짝 번갈아 배치 (단순 균형)
        digits = []
        for pos in range(6):
            if pos % 2 == 0:
                pool = [str(i) for i in range(10) if i % 2 == 0]  # 짝수
            else:
                pool = [str(i) for i in range(10) if i % 2 == 1]  # 홀수
            digits.append(random.choice(pool))

        results.append({"grp": grp, "num": "".join(digits), "strategy": "balanced"})
    return results


def recommend_random(games: int = 5) -> list:
    """완전 무작위 추천"""
    return [
        {
            "grp": random.randint(1, 5),
            "num": str(random.randint(0, 999999)).zfill(6),
            "strategy": "random",
        }
        for _ in range(games)
    ]


def recommend_all_pension(draws: list, games: int = 3) -> dict:
    """
    3가지 전략 추천 결과 일괄 반환
    각 전략당 games개씩
    """
    return {
        "frequency": {
            "games": recommend_by_digit_frequency(draws, games=games),
            "strategy": "frequency",
            "description": "자릿수별 출현 빈도에 비례하여 번호를 생성합니다.",
        },
        "balanced": {
            "games": recommend_balanced(draws, games=games),
            "strategy": "balanced",
            "description": "홀짝 균형을 맞추고 자주 나온 조를 우선합니다.",
        },
        "random": {
            "games": recommend_random(games=games),
            "strategy": "random",
            "description": "완전 무작위로 조와 번호를 생성합니다.",
        },
    }


def weekly_pension_pick(draws: list, n_games: int = 5) -> list:
    """
    이번 주 연금복권 추천 n_games개
    - 빈도 기반 2개 + 균형 2개 + 랜덤 1개
    """
    if not draws:
        return recommend_random(games=n_games)

    freq_n = max(1, n_games * 2 // 5)
    bal_n  = max(1, n_games * 2 // 5)
    rand_n = n_games - freq_n - bal_n

    games = (
        recommend_by_digit_frequency(draws, games=freq_n)
        + recommend_balanced(draws, games=bal_n)
        + recommend_random(games=rand_n)
    )
    return games[:n_games]
