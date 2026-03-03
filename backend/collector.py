"""
동행복권 신 API 크롤러
- URL: GET https://www.dhlottery.co.kr/lt645/selectPstLt645InfoNew.do?srchLtEpsd={회차}
- srchLtEpsd 지정 시 해당 회차 포함 이전 최대 10개 반환
- srchLtEpsd 미지정 시 빈 리스트 반환
"""
import io
import time
import requests
import logging
from typing import Optional
from config import settings

logger = logging.getLogger(__name__)

NEW_API_URL = "https://www.dhlottery.co.kr/lt645/selectPstLt645InfoNew.do"

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.dhlottery.co.kr/",
})


def _parse_item(item: dict) -> Optional[dict]:
    """API 응답 item 한 건 → DB upsert 형식으로 변환"""
    try:
        ymd = str(item.get("ltRflYmd", ""))
        draw_date = f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:8]}" if len(ymd) == 8 else ""

        return {
            "round":       int(item["ltEpsd"]),
            "draw_date":   draw_date,
            "num1":        int(item["tm1WnNo"]),
            "num2":        int(item["tm2WnNo"]),
            "num3":        int(item["tm3WnNo"]),
            "num4":        int(item["tm4WnNo"]),
            "num5":        int(item["tm5WnNo"]),
            "num6":        int(item["tm6WnNo"]),
            "bonus":       int(item["bnsWnNo"]),
            "total_prize": int(item["rlvtEpsdSumNtslAmt"]) if item.get("rlvtEpsdSumNtslAmt") else None,
            "win1_count":  int(item["rnk1WnNope"]) if item.get("rnk1WnNope") is not None else None,
            "win1_prize":  int(item["rnk1WnAmt"]) if item.get("rnk1WnAmt") else None,
        }
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"[collector] item 파싱 오류: {e} — {item}")
        return None


def fetch_draw(round_no: int) -> Optional[dict]:
    """
    단일 회차 당첨 번호 조회
    반환: dict | None (실패 시)
    """
    try:
        resp = _SESSION.get(NEW_API_URL, params={"srchLtEpsd": round_no}, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        lst = data.get("data", {}).get("list", [])
        # list에는 해당 회차 포함 이전 최대 10개가 오므로 정확히 일치하는 것만 추출
        for item in lst:
            if item.get("ltEpsd") == round_no:
                return _parse_item(item)
        return None

    except requests.RequestException as e:
        logger.error(f"[collector] round {round_no} 요청 실패: {e}")
        return None


def fetch_latest_round() -> int:
    """
    현재까지 진행된 최신 회차 번호를 이진 탐색으로 파악
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


def fetch_range_batch(round_no: int) -> list[dict]:
    """
    신 API는 srchLtEpsd 지정 시 해당 회차 포함 이전 최대 10개를 한 번에 반환.
    해당 회차를 기준으로 일괄 조회해서 효율적으로 수집.
    반환: 파싱 성공한 회차 리스트 (회차 오름차순)
    """
    try:
        resp = _SESSION.get(NEW_API_URL, params={"srchLtEpsd": round_no}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        lst = data.get("data", {}).get("list", [])

        results = []
        for item in lst:
            parsed = _parse_item(item)
            if parsed:
                results.append(parsed)

        return sorted(results, key=lambda x: x["round"])

    except requests.RequestException as e:
        logger.error(f"[collector] batch {round_no} 요청 실패: {e}")
        return []


def collect_range(start: int, end: int, delay: float = None) -> list[dict]:
    """
    start ~ end 회차 범위 수집
    신 API는 10개씩 일괄 반환되므로 end 기준으로 역방향 배치 수집.
    반환: 성공한 회차 리스트 (오름차순)
    """
    if delay is None:
        delay = settings.COLLECT_DELAY_SEC

    collected: dict[int, dict] = {}

    # end부터 start까지 10회씩 끊어서 배치 조회
    cursor = end
    while cursor >= start:
        batch = fetch_range_batch(cursor)
        for item in batch:
            r = item["round"]
            if start <= r <= end:
                collected[r] = item

        # 다음 배치: 현재 배치에서 가장 작은 회차 - 1
        if batch:
            cursor = min(item["round"] for item in batch) - 1
        else:
            # 배치가 비어있으면 10 내려서 재시도
            cursor -= 10

        if cursor < start:
            break
        time.sleep(delay)

    result = sorted(collected.values(), key=lambda x: x["round"])
    logger.info(f"[collector] {start}~{end} 범위 {len(result)}회차 수집 완료")
    return result


# ─────────────────────────────────────────────
# 엑셀 파서 (동행복권 공식 xlsx)
# 컬럼: No | 회차 | num1~6 | 보너스 | 순위 | 당첨게임수 | 1게임당 당첨금액
# ─────────────────────────────────────────────

def _parse_prize_str(val) -> Optional[int]:
    """'1,740,011,646 원' 또는 숫자 → int"""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return int(val)
    s = str(val).replace(",", "").replace("원", "").replace(" ", "")
    try:
        return int(s)
    except ValueError:
        return None


def _parse_count_str(val) -> Optional[int]:
    """'18 명' 또는 숫자 → int"""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return int(val)
    s = str(val).replace("명", "").replace(" ", "")
    try:
        return int(s)
    except ValueError:
        return None


def parse_xlsx(file_bytes: bytes) -> list[dict]:
    """
    동행복권 공식 엑셀 파싱
    컬럼: A=No, B=회차, C~H=번호1~6, I=보너스, J=순위, K=당첨게임수, L=1게임당 당첨금액
    반환: DB upsert 형식 리스트
    """
    try:
        import openpyxl
    except ImportError:
        raise RuntimeError("openpyxl 패키지가 필요합니다: pip install openpyxl")

    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    ws = wb.active

    results = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or row[1] is None:
            continue
        try:
            round_no = int(row[1])
            nums = sorted([int(row[2]), int(row[3]), int(row[4]),
                           int(row[5]), int(row[6]), int(row[7])])
            bonus      = int(row[8])
            win1_count = _parse_count_str(row[10])
            win1_prize = _parse_prize_str(row[11])

            results.append({
                "round":       round_no,
                "draw_date":   "",   # 엑셀에 날짜 없음 — collect_range 호출로 보완 가능
                "num1":        nums[0],
                "num2":        nums[1],
                "num3":        nums[2],
                "num4":        nums[3],
                "num5":        nums[4],
                "num6":        nums[5],
                "bonus":       bonus,
                "total_prize": None,
                "win1_count":  win1_count,
                "win1_prize":  win1_prize,
            })
        except (TypeError, ValueError, IndexError) as e:
            logger.warning(f"[xlsx] 행 파싱 스킵: {e} — {row}")
            continue

    logger.info(f"[xlsx] {len(results)}회차 파싱 완료")
    return results


def parse_csv_row(row: dict) -> Optional[dict]:
    """
    CSV 파일 행 → DB upsert 형식으로 변환
    예상 컬럼: 회차, 추첨일, 번호1~6, 보너스
    """
    try:
        col_map = {
            "회차": "round", "추첨일": "draw_date",
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
