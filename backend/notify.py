"""
디스코드 웹훅 전송 모듈 (embed 방식)
- WEBHOOK_RECOMMEND         : 로또 매주 추천번호 전송
- WEBHOOK_RESULT            : 로또 당첨/낙첨 결과 전송
- WEBHOOK_PENSION_RECOMMEND : 연금복권 매주 추천번호 전송
- WEBHOOK_PENSION_RESULT    : 연금복권 당첨/낙첨 결과 전송
"""
import logging
import requests

logger = logging.getLogger(__name__)

WEBHOOK_RECOMMEND = (
    "https://discord.com/api/webhooks/1478316402287837204/"
    "VnL3nukXY86eMmWXLEARNXBkoeZFgAq4hFLQF8TuL8dzI4QJVXIqHzAH-5XMeAMiA1SU"
)
WEBHOOK_RESULT = (
    "https://discord.com/api/webhooks/1478316807982157941/"
    "AWw9EWkeOBLF9SFfapNIo1DEsV6JrHEa3w81GMXi1FjEdt-rY8dd-2FslPc3Lhp2s8Cx"
)
WEBHOOK_PENSION_RECOMMEND = (
    "https://discord.com/api/webhooks/1479376110256001066/"
    "u2uEROrYee4VkJPGz9y0_tUkcB1Li2xV-PpeKIaUu4VBjZrfUh-b06LgQD4cIKTWyFEM"
)
WEBHOOK_PENSION_RESULT = (
    "https://discord.com/api/webhooks/1479376257492844706/"
    "lE3aT_4CbEEw9BhDHXgwFXXzBlGo9N5OwMBO_amp1s-gRXjf3YzzxA5eOMfHDR3-7uIo"
)


def _nums(nums: list) -> str:
    """번호 리스트 → '05  11  25  27  36  38' 형태"""
    return "  ".join(f"**{n:02d}**" for n in sorted(nums))


def _post(url: str, payload: dict) -> bool:
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code in (200, 204):
            logger.info(f"[notify] 전송 완료 HTTP {resp.status_code}")
            return True
        else:
            logger.error(f"[notify] HTTP {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        logger.error(f"[notify] 전송 오류: {e}")
        return False


# ── 주간 추천번호 전송 ────────────────────────────
def send_weekly_numbers(
    latest_round: int,
    latest_numbers: list,
    latest_bonus: int,
    fixed_numbers: list,
    condition_games: list,   # 조건 추천 4게임
    pattern_games: list,     # 패턴 추천 5게임
    next_round: int,
) -> bool:

    condition_text = "\n".join(
        f"`{i:02d}`  {_nums(game)}"
        for i, game in enumerate(condition_games, 1)
    )
    pattern_text = "\n".join(
        f"`{i:02d}`  {_nums(game)}"
        for i, game in enumerate(pattern_games, 1)
    )

    payload = {
        "embeds": [{
            "title": f"🎱  로또 {next_round}회 번호 추천",
            "color": 0x3498db,
            "fields": [
                {
                    "name": f"📋  {latest_round}회 지난주 당첨번호",
                    "value": f"{_nums(latest_numbers)}  **+**  **{latest_bonus:02d}**",
                    "inline": False,
                },
                {
                    "name": "🔒  고정번호 (매주 동일)",
                    "value": _nums(fixed_numbers),
                    "inline": False,
                },
                {
                    "name": f"🤖  조건 추천 {len(condition_games)}게임  (WEIGHTED_RECENT)",
                    "value": condition_text or "—",
                    "inline": False,
                },
                {
                    "name": f"📈  패턴 추천 {len(pattern_games)}게임  (합계 신호 기반)",
                    "value": pattern_text or "—",
                    "inline": False,
                },
            ],
            "footer": {"text": "lottery.web-bro.com"},
        }]
    }
    return _post(WEBHOOK_RECOMMEND, payload)


# ── 당첨/낙첨 결과 전송 ───────────────────────────
def send_result(
    target_round: int,
    actual_numbers: list,
    actual_bonus: int,
    fixed_numbers: list,
    result_detail: list,
) -> bool:

    RANK_LABEL = {1: "🥇 1등", 2: "🥈 2등", 3: "🥉 3등", 4: "4등  ", 5: "5등  ", 0: "낙첨  "}

    # 등수별 집계
    rank_counts = {}
    for r in result_detail:
        rank_counts[r["rank"]] = rank_counts.get(r["rank"], 0) + 1

    # 고정번호 결과
    fixed_result = next((r for r in result_detail if r.get("is_fixed")), None)
    fixed_rank    = fixed_result["rank"] if fixed_result else 0
    fixed_matched = fixed_result["matched"] if fixed_result else 0

    # 추천번호 결과 텍스트 (source_label 포함)
    rec_lines = []
    for r in result_detail:
        if r.get("is_fixed"):
            continue
        label = RANK_LABEL.get(r["rank"], "낙첨  ")
        src = r.get("source_label", "")
        tag = f"[{src}]  " if src else ""
        rec_lines.append(f"`{label}`  {tag}{_nums(r['game'])}  `{r['matched']}개 일치`")
    rec_text = "\n".join(rec_lines) if rec_lines else "—"

    # 헤더 색상
    best_rank = min((r["rank"] for r in result_detail if r["rank"] > 0), default=0)
    if best_rank == 1:
        color, header = 0xf1c40f, "🎉  1등 당첨!!"
    elif best_rank == 2:
        color, header = 0xe67e22, "🎉  2등 당첨!"
    elif best_rank == 3:
        color, header = 0x2ecc71, "🎊  3등 당첨!"
    elif best_rank in (4, 5):
        color, header = 0x3498db, f"🎊  {best_rank}등 당첨!"
    else:
        color, header = 0x95a5a6, "😔  이번 주는 낙첨"

    # 집계 문자열
    summary_parts = []
    for k in [1, 2, 3, 4, 5, 0]:
        cnt = rank_counts.get(k, 0)
        if cnt:
            summary_parts.append(f"{RANK_LABEL[k].strip()}: {cnt}게임")
    summary = "  |  ".join(summary_parts)

    payload = {
        "embeds": [{
            "title": f"🎱  로또 {target_round}회 결과",
            "description": header,
            "color": color,
            "fields": [
                {
                    "name": f"📋  {target_round}회 실제 당첨번호",
                    "value": f"{_nums(actual_numbers)}  **+**  **{actual_bonus:02d}**",
                    "inline": False,
                },
                {
                    "name": "🔒  고정번호 결과",
                    "value": f"{_nums(fixed_numbers)}  →  `{RANK_LABEL[fixed_rank].strip()}` ({fixed_matched}개 일치)",
                    "inline": False,
                },
                {
                    "name": f"🤖  추천번호 결과 ({len(rec_lines)}게임)",
                    "value": rec_text,
                    "inline": False,
                },
                {
                    "name": "📊  집계",
                    "value": summary or "전체 낙첨",
                    "inline": False,
                },
            ],
            "footer": {"text": "lottery.web-bro.com"},
        }]
    }
    return _post(WEBHOOK_RESULT, payload)


# ── 연금복권 주간 추천번호 전송 ──────────────────────
def send_pension_weekly_numbers(
    latest_round: int,
    latest_grp: int,
    latest_num: str,
    pick: dict,           # {"grp":2,"num":"331316","strategy":"hot","score":72.5}
    next_round: int,
) -> bool:
    """연금복권720+ 주간 추천번호 디스코드 전송 (최적 1개 조합)"""

    strategy_label = {
        "hot":         "빈도 우선",
        "prefix_fix":  "앞자리 패턴",
        "sum_range":   "합계 범위",
        "cold_hot":    "콜드-핫 혼합",
        "random":      "랜덤",
    }.get(pick.get("strategy", ""), pick.get("strategy", ""))

    score = pick.get("score", 0)
    grp   = pick.get("grp", "?")
    num   = str(pick.get("num", "000000")).zfill(6)

    payload = {
        "embeds": [{
            "title": f"💰  연금복권720+ {next_round}회 번호 추천",
            "color": 0x2ecc71,
            "fields": [
                {
                    "name": f"📋  {latest_round}회 지난주 당첨번호",
                    "value": f"**{latest_grp}조**  `{str(latest_num).zfill(6)}`",
                    "inline": False,
                },
                {
                    "name": "🎯  이번 주 최적 추천 (모든조 5장씩)",
                    "value": f"## **모든조(1~5)  {num}**",
                    "inline": False,
                },
                {
                    "name": "📊  추천 근거",
                    "value": f"후보 20개 중 최적 선정  |  전략: {strategy_label}",
                    "inline": False,
                },
            ],
            "footer": {"text": "lottery.web-bro.com  |  매주 목요일 추첨"},
        }]
    }
    return _post(WEBHOOK_PENSION_RECOMMEND, payload)


# ── 연금복권 당첨/낙첨 결과 전송 ──────────────────────
def send_pension_result(
    target_round: int,
    actual_grp: int,
    actual_num: str,
    actual_bonus: str,
    result_detail: list,  # [{"game":{"grp":2,"num":"331316"},"rank":0}, ...]
) -> bool:
    """연금복권720+ 당첨 결과 디스코드 전송"""

    RANK_LABEL = {
        1: "🥇 1등", 2: "🥈 2등", 3: "🥉 3등",
        4: "4등  ", 5: "5등  ", 6: "6등  ", 7: "7등  ", 0: "낙첨  ",
    }

    rank_counts: dict = {}
    for r in result_detail:
        rank_counts[r["rank"]] = rank_counts.get(r["rank"], 0) + 1

    best_rank = min((r["rank"] for r in result_detail if r["rank"] > 0), default=0)
    if best_rank == 1:
        color, header = 0xf1c40f, "🎉  1등 당첨!!"
    elif best_rank == 2:
        color, header = 0xe67e22, "🎉  2등 당첨!"
    elif best_rank == 3:
        color, header = 0x2ecc71, "🎊  3등 당첨!"
    elif best_rank in (4, 5, 6, 7):
        color, header = 0x3498db, f"🎊  {best_rank}등 당첨!"
    else:
        color, header = 0x95a5a6, "😔  이번 주는 낙첨"

    rec_lines = []
    for r in result_detail:
        g = r.get("game", {})
        lbl = RANK_LABEL.get(r["rank"], "낙첨  ")
        rec_lines.append(f"`{lbl}`  **{g.get('grp','?')}조**  `{str(g.get('num','?')).zfill(6)}`")
    rec_text = "\n".join(rec_lines) if rec_lines else "—"

    summary_parts = []
    for k in [1, 2, 3, 4, 5, 6, 7, 0]:
        cnt = rank_counts.get(k, 0)
        if cnt:
            summary_parts.append(f"{RANK_LABEL[k].strip()}: {cnt}게임")
    summary = "  |  ".join(summary_parts)

    payload = {
        "embeds": [{
            "title": f"💰  연금복권720+ {target_round}회 결과",
            "description": header,
            "color": color,
            "fields": [
                {
                    "name": f"📋  {target_round}회 실제 당첨번호",
                    "value": f"**{actual_grp}조**  `{str(actual_num).zfill(6)}`  (보너스: `{str(actual_bonus).zfill(6)}`)",
                    "inline": False,
                },
                {
                    "name": f"🎰  추천번호 결과 ({len(rec_lines)}게임)",
                    "value": rec_text,
                    "inline": False,
                },
                {
                    "name": "📊  집계",
                    "value": summary or "전체 낙첨",
                    "inline": False,
                },
            ],
            "footer": {"text": "lottery.web-bro.com"},
        }]
    }
    return _post(WEBHOOK_PENSION_RESULT, payload)


# ── 오류 알림 ────────────────────────────────────
def send_error(message: str):
    _post(WEBHOOK_RESULT, {
        "embeds": [{
            "title": "⚠️  Lottery 주간 작업 오류",
            "description": f"```\n{message}\n```",
            "color": 0xe74c3c,
        }]
    })
