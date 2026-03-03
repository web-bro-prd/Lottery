"""
디스코드 웹훅 전송 모듈
- WEBHOOK_RECOMMEND : 매주 추천번호 전송
- WEBHOOK_RESULT    : 당첨/낙첨 결과 전송
"""
import json
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


# ── 번호 → 이모지 공 ──────────────────────────────
def _ball(n: int) -> str:
    if n <= 10:  return f"🟡`{n:02d}`"
    if n <= 20:  return f"🔵`{n:02d}`"
    if n <= 30:  return f"🔴`{n:02d}`"
    if n <= 40:  return f"⬛`{n:02d}`"
    return              f"🟢`{n:02d}`"


def _balls(nums: list) -> str:
    return " ".join(_ball(n) for n in sorted(nums))


def _post(url: str, content: str) -> bool:
    try:
        resp = requests.post(
            url,
            json={"content": content},
            timeout=10,
        )
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

    rec_lines = []
    for i, (game, score) in enumerate(zip(recommend_games, recommend_scores), 1):
        rec_lines.append(
            f"> **{i:02d}** {_balls(game)}  `{score*100:.0f}%`"
        )

    lines = [
        f"# 🎱 로또 {next_round}회 번호 추천",
        "",
        f"## 📋 {latest_round}회 지난주 당첨번호",
        f"> {_balls(latest_numbers)}  **+** {_ball(latest_bonus)}",
        "",
        "## 🔒 고정 구매 번호",
        f"> {_balls(fixed_numbers)}",
        "",
        f"## 🤖 WEIGHTED\\_RECENT 추천 {len(recommend_games)}게임",
    ] + rec_lines + [
        "",
        "-# lottery.web-bro.com",
    ]
    return _post(WEBHOOK_RECOMMEND, "\n".join(lines))


# ── 당첨/낙첨 결과 전송 ───────────────────────────
def send_result(
    target_round: int,
    actual_numbers: list,
    actual_bonus: int,
    fixed_numbers: list,
    result_detail: list,   # [{"game": [..], "rank": 0, "matched": 2}, ...]
) -> bool:

    RANK_LABEL = {1: "🥇 1등", 2: "🥈 2등", 3: "🥉 3등", 4: "4등", 5: "5등", 0: "낙첨"}
    RANK_PRIZE = {1: "약 20억", 2: "약 5500만", 3: "약 150만", 4: "5만원", 5: "5천원", 0: "—"}

    # 등수별 집계
    rank_counts = {0: 0, 5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    for r in result_detail:
        rank_counts[r["rank"]] = rank_counts.get(r["rank"], 0) + 1

    # 고정번호 결과
    fixed_result = next((r for r in result_detail if r.get("is_fixed")), None)
    fixed_rank   = fixed_result["rank"] if fixed_result else 0
    fixed_matched = fixed_result["matched"] if fixed_result else 0

    # 추천번호 결과 라인
    rec_lines = []
    for r in result_detail:
        if r.get("is_fixed"):
            continue
        label = RANK_LABEL.get(r["rank"], "낙첨")
        rec_lines.append(
            f"> {_balls(r['game'])}  → **{label}** ({r['matched']}개 일치)"
        )

    # 당첨 있으면 축하 문구
    best_rank = min(r["rank"] if r["rank"] > 0 else 99 for r in result_detail)
    if best_rank <= 3:
        header = f"🎉 **{RANK_LABEL[best_rank]} 당첨!!**"
    elif best_rank <= 5:
        header = f"🎊 **{RANK_LABEL[best_rank]} 당첨!**"
    else:
        header = "😔 이번 주는 낙첨"

    lines = [
        f"# 🎱 로또 {target_round}회 결과",
        header,
        "",
        f"## 📋 {target_round}회 실제 당첨번호",
        f"> {_balls(actual_numbers)}  **+** {_ball(actual_bonus)}",
        "",
        f"## 🔒 고정번호 결과",
        f"> {_balls(fixed_numbers)}  → **{RANK_LABEL[fixed_rank]}** ({fixed_matched}개 일치)",
        "",
        f"## 🤖 추천번호 결과 ({len(rec_lines)}게임)",
    ] + rec_lines + [
        "",
        f"**집계** | " + " | ".join(
            f"{RANK_LABEL[k]}: {v}회" for k, v in sorted(rank_counts.items())
            if k > 0 and v > 0
        ) + (f" | 낙첨: {rank_counts[0]}회" if rank_counts[0] > 0 else ""),
        "",
        "-# lottery.web-bro.com",
    ]
    return _post(WEBHOOK_RESULT, "\n".join(lines))


# ── 오류 알림 ────────────────────────────────────
def send_error(message: str):
    _post(WEBHOOK_RESULT, f"⚠️ **Lottery 주간 작업 오류**\n```\n{message}\n```")
