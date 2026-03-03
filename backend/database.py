import sqlite3
import os
from config import settings


def get_db():
    """DB 연결 반환"""
    os.makedirs(os.path.dirname(settings.DB_PATH), exist_ok=True)
    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """DB 초기화 — 테이블 생성"""
    conn = get_db()
    cur = conn.cursor()

    # 당첨 번호 테이블
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tbl_draw (
            round       INTEGER PRIMARY KEY,   -- 회차
            draw_date   TEXT NOT NULL,          -- 추첨일 (YYYY-MM-DD)
            num1        INTEGER NOT NULL,
            num2        INTEGER NOT NULL,
            num3        INTEGER NOT NULL,
            num4        INTEGER NOT NULL,
            num5        INTEGER NOT NULL,
            num6        INTEGER NOT NULL,
            bonus       INTEGER NOT NULL,       -- 보너스 번호
            total_prize INTEGER,                -- 1등 총 당첨금
            win1_count  INTEGER,                -- 1등 당첨자 수
            win1_prize  INTEGER,                -- 1등 1인당 당첨금
            created_at  TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    # CSV 업로드 이력 테이블
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tbl_upload_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            filename    TEXT NOT NULL,
            rounds      INTEGER NOT NULL,       -- 업로드된 회차 수
            uploaded_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    conn.commit()
    conn.close()


def get_latest_round() -> int:
    """DB에 저장된 최신 회차 반환 (없으면 0)"""
    conn = get_db()
    row = conn.execute("SELECT MAX(round) as max_round FROM tbl_draw").fetchone()
    conn.close()
    return row["max_round"] or 0


def upsert_draw(data: dict):
    """당첨 번호 upsert"""
    conn = get_db()
    conn.execute("""
        INSERT OR REPLACE INTO tbl_draw
            (round, draw_date, num1, num2, num3, num4, num5, num6, bonus,
             total_prize, win1_count, win1_prize)
        VALUES
            (:round, :draw_date, :num1, :num2, :num3, :num4, :num5, :num6, :bonus,
             :total_prize, :win1_count, :win1_prize)
    """, data)
    conn.commit()
    conn.close()


def get_all_draws() -> list[dict]:
    """전체 회차 데이터 반환"""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM tbl_draw ORDER BY round ASC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_draws_by_range(start: int, end: int) -> list[dict]:
    """특정 회차 범위 데이터 반환"""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM tbl_draw WHERE round BETWEEN ? AND ? ORDER BY round ASC",
        (start, end)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
