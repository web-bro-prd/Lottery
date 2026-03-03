"""
동행복권 API 크롤러
- 동행복권 공식 API: GET https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={round}
- 응답: JSON (returnValue: "success" | "fail")
"""
import time
import requests
import logging
from typing import Optional
from config import settings

logger = logging.getLogger(__name__)

LOTTO_API_URL = settings.LOTTO_API_URL


def fetch_draw(round_no: int) -> Optional[dict]:
    """
    단일 회차 당첨 번호 조회
    반환: dict | None (실패 시)
    """
    try:
        resp = requests.get(
            LOTTO_API_URL,
            params={"method": "getLottoNumber", "drwNo": round_no},
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("returnValue") != "success":
            return None

        return {
            "round":       data["drwNo"],
            "draw_date":   data["drwNoDate"],
            "num1":        data["drwtNo1"],
            "num2":        data["drwtNo2"],
            "num3":        data["drwtNo3"],
            "num4":        data["drwtNo4"],
            "num5":        data["drwtNo5"],
            "num6":        data["drwtNo6"],
            "bonus":       data["bnusNo"],
            "total_prize": data.get("totSellamnt"),        # 총 판매금액
            "win1_count":  data.get("firstPrzwnerCo"),     # 1등 당첨자 수
            "win1_prize":  data.get("firstWinamnt"),       # 1등 당첨금
        }

    except requests.RequestException as e:
        logger.error(f"[collector] round {round_no} 요청 실패: {e}")
        return None
    except Exception as e:
        logger.error(f"[collector] round {round_no} 파싱 오류: {e}")
        return None


def fetch_latest_round() -> int:
    """
    현재까지 진행된 최신 회차 번호를 동적으로 파악
    - 최신 회차는 이진 탐색으로 찾음 (1~2000 범위)
    """
    lo, hi = 1, 2000
    latest = 1

    while lo <= hi:
        mid = (lo + hi) // 2
        data = fetch_draw(mid)
        if data:
            latest = mid
            lo = mid + 1
        else:
            hi = mid - 1
        time.sleep(0.1)

    return latest


def collect_range(start: int, end: int, delay: float = None) -> list[dict]:
    """
    start ~ end 회차 범위 수집
    반환: 성공한 회차 리스트
    """
    if delay is None:
        delay = settings.COLLECT_DELAY_SEC

    results = []
    for round_no in range(start, end + 1):
        data = fetch_draw(round_no)
        if data:
            results.append(data)
            logger.info(f"[collector] {round_no}회 수집 완료")
        else:
            logger.warning(f"[collector] {round_no}회 수집 실패 — 종료")
            break   # API가 없는 회차에서 중단
        time.sleep(delay)

    return results


def parse_csv_row(row: dict) -> Optional[dict]:
    """
    CSV 파일 행 → DB upsert 형식으로 변환
    예상 컬럼: 회차, 추첨일, 번호1~6, 보너스
    """
    try:
        # 컬럼명 정규화 (다양한 CSV 포맷 지원)
        col_map = {
            "회차": "round",
            "추첨일": "draw_date",
            "번호1": "num1", "1번": "num1",
            "번호2": "num2", "2번": "num2",
            "번호3": "num3", "3번": "num3",
            "번호4": "num4", "4번": "num4",
            "번호5": "num5", "5번": "num5",
            "번호6": "num6", "6번": "num6",
            "보너스": "bonus", "보너스번호": "bonus",
            "1등당첨자수": "win1_count",
            "1등당첨금": "win1_prize",
        }

        normalized = {}
        for k, v in row.items():
            key = col_map.get(k.strip(), k.strip())
            normalized[key] = v

        return {
            "round":       int(normalized["round"]),
            "draw_date":   str(normalized.get("draw_date", "")),
            "num1":        int(normalized["num1"]),
            "num2":        int(normalized["num2"]),
            "num3":        int(normalized["num3"]),
            "num4":        int(normalized["num4"]),
            "num5":        int(normalized["num5"]),
            "num6":        int(normalized["num6"]),
            "bonus":       int(normalized["bonus"]),
            "total_prize": None,
            "win1_count":  int(normalized["win1_count"]) if "win1_count" in normalized else None,
            "win1_prize":  int(normalized["win1_prize"]) if "win1_prize" in normalized else None,
        }

    except (KeyError, ValueError) as e:
        logger.error(f"[collector] CSV 파싱 오류: {e} — 행: {row}")
        return None
