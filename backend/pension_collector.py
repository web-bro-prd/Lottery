"""
연금복권720+ 데이터 수집 모듈
- 공개 API: GET https://www.dhlottery.co.kr/pt720/selectPstPt720WnList.do
  → 파라미터 없이 호출하면 전체 회차 JSON 반환
- 응답 필드:
    psltEpsd  : 회차 (int)
    psltRflYmd: 추첨일 YYYYMMDD
    wnBndNo   : 당첨 조 (str "1"~"5")
    wnRnkVl   : 당첨 6자리 번호 (str)
    bnsRnkVl  : 보너스 6자리 번호 (str)
"""
import io
import logging
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

PENSION_API_URL = "https://www.dhlottery.co.kr/pt720/selectPstPt720WnList.do"

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.dhlottery.co.kr/",
})


def _parse_item(item: dict) -> Optional[dict]:
    """API 응답 item 한 건 → DB upsert 형식"""
    try:
        ymd = str(item.get("psltRflYmd", ""))
        draw_date = f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:8]}" if len(ymd) == 8 else ""
        return {
            "round":     int(item["psltEpsd"]),
            "draw_date": draw_date,
            "grp":       int(item["wnBndNo"]),
            "num":       str(item["wnRnkVl"]).zfill(6),
            "bonus_num": str(item["bnsRnkVl"]).zfill(6),
        }
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"[pension_collector] 파싱 오류: {e} — {item}")
        return None


def fetch_all_pension() -> list:
    """
    API 호출 → 전체 회차 목록 반환 (오름차순)
    """
    try:
        resp = _SESSION.get(PENSION_API_URL, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("data", {}).get("result", [])
        results = []
        for item in items:
            parsed = _parse_item(item)
            if parsed:
                results.append(parsed)
        results.sort(key=lambda x: x["round"])
        logger.info(f"[pension_collector] 전체 {len(results)}회차 수집 완료")
        return results
    except requests.RequestException as e:
        logger.error(f"[pension_collector] API 요청 실패: {e}")
        return []


def fetch_latest_pension() -> Optional[dict]:
    """
    가장 최신 1회차 데이터 반환
    """
    try:
        resp = _SESSION.get(PENSION_API_URL, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("data", {}).get("result", [])
        if not items:
            return None
        # psltEpsd 기준 최대값
        latest = max(items, key=lambda x: int(x.get("psltEpsd", 0)))
        return _parse_item(latest)
    except requests.RequestException as e:
        logger.error(f"[pension_collector] 최신 회차 요청 실패: {e}")
        return None


def fetch_latest_pension_round() -> int:
    """최신 회차 번호만 반환 (없으면 0)"""
    item = fetch_latest_pension()
    return item["round"] if item else 0


def fetch_new_pension_draws(db_latest: int) -> list:
    """
    DB에 없는 신규 회차만 수집하여 반환
    """
    all_draws = fetch_all_pension()
    new = [d for d in all_draws if d["round"] > db_latest]
    logger.info(f"[pension_collector] 신규 {len(new)}회차 (DB최신={db_latest})")
    return new


# ─────────────────────────────────────────────
# 엑셀 파서 (동행복권 공식 xlsx: No | 회차 | 조 | 당첨번호)
# ─────────────────────────────────────────────

def parse_pension_xlsx(file_bytes: bytes) -> list:
    """
    연금복권720+ 공식 엑셀 파일 파싱
    컬럼: A=No, B=회차, C=조, D=당첨번호
    보너스번호는 엑셀에 없으므로 API 데이터로 보완하거나 빈 문자열로 저장
    """
    try:
        import openpyxl
    except ImportError:
        raise RuntimeError("openpyxl 패키지가 필요합니다: pip install openpyxl")

    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    ws = wb.active

    # API에서 전체 데이터 가져와 보너스 번호 보완
    api_data = {}
    try:
        all_draws = fetch_all_pension()
        api_data = {d["round"]: d for d in all_draws}
    except Exception:
        pass

    results = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or row[1] is None:
            continue
        try:
            round_no = int(float(str(row[1])))
            grp = int(float(str(row[2]))) if row[2] is not None else 0
            num = str(row[3]).zfill(6) if row[3] is not None else "000000"

            # 보너스 번호: API 데이터에서 가져오기, 없으면 빈 문자열
            bonus_num = api_data.get(round_no, {}).get("bonus_num", "")

            results.append({
                "round":     round_no,
                "draw_date": api_data.get(round_no, {}).get("draw_date", ""),
                "grp":       grp,
                "num":       num,
                "bonus_num": bonus_num,
            })
        except (TypeError, ValueError, IndexError) as e:
            logger.warning(f"[pension_xlsx] 행 파싱 스킵: {e} — {row}")
            continue

    logger.info(f"[pension_xlsx] {len(results)}회차 파싱 완료")
    return results


def parse_pension_csv_row(row: dict) -> Optional[dict]:
    """
    CSV 행 파싱
    예상 컬럼: 회차, 추첨일, 조, 당첨번호, 보너스번호
    """
    try:
        col_map = {
            "회차": "round", "추첨일": "draw_date",
            "조": "grp", "당첨번호": "num", "보너스번호": "bonus_num",
        }
        normalized = {}
        for k, v in row.items():
            key = col_map.get(k.strip(), k.strip())
            normalized[key] = v

        return {
            "round":     int(normalized["round"]),
            "draw_date": str(normalized.get("draw_date", "")),
            "grp":       int(normalized.get("grp", 0)),
            "num":       str(normalized.get("num", "")).zfill(6),
            "bonus_num": str(normalized.get("bonus_num", "")).zfill(6),
        }
    except (KeyError, ValueError) as e:
        logger.error(f"[pension_collector] CSV 파싱 오류: {e}")
        return None
