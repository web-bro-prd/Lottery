"""
디스코드 웹훅 전송 모듈 (embed 방식)
- WEBHOOK_RECOMMEND : 매주 추천번호 전송
- WEBHOOK_RESULT    : 당첨/낙첨 결과 전송
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
    recommend_games: list,
    recommend_scores: list,
    next_round: int,
) -> bool:

    # 추천번호 필드 (3게임씩 2열)
    rec_text = "\n".join(
        f"`{i:02d}`  {_nums(game)}  `{score*100:.0f}%`"
        for i, (game, score) in enumerate(zip(recommend_games, recommend_scores), 1)
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
                    "name": "🔒  고정 구매 번호 (매주 동일)",
                    "value": _nums(fixed_numbers),
                    "inline": False,
                },
                {
                    "name": f"🤖  WEIGHTED_RECENT 추천 {len(recommend_games)}게임",
                    "value": rec_text,
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

    # 추천번호 결과 텍스트
    rec_lines = []
    for r in result_detail:
        if r.get("is_fixed"):
            continue
        label = RANK_LABEL.get(r["rank"], "낙첨  ")
        rec_lines.append(f"`{label}`  {_nums(r['game'])}  `{r['matched']}개 일치`")
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


# ── 오류 알림 ────────────────────────────────────
def send_error(message: str):
    _post(WEBHOOK_RESULT, {
        "embeds": [{
            "title": "⚠️  Lottery 주간 작업 오류",
            "description": f"```\n{message}\n```",
            "color": 0xe74c3c,
        }]
    })
