import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

logger = logging.getLogger("call_sessions")
_DB_DIR = Path(__file__).parent.parent / "data"
_DB_PATH = _DB_DIR / "mo_saathi.db"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _anon_id(user_id: str) -> str:
    """Return a short anonymous token so the dashboard never exposes real IDs."""
    return hashlib.sha256(user_id.encode()).hexdigest()[:8].upper()


# ---------------------------------------------------------------------------
# Table setup + safe migration
# ---------------------------------------------------------------------------

async def init_sessions_table() -> None:
    """Create call_sessions table; safely add new columns to existing DB."""
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS call_sessions (
                session_id         TEXT PRIMARY KEY,
                user_id            TEXT NOT NULL DEFAULT '',
                call_type          TEXT NOT NULL DEFAULT 'inbound',
                language           TEXT NOT NULL DEFAULT 'od-IN',
                outcome            TEXT NOT NULL DEFAULT 'in_progress',
                exercise_attempted INTEGER NOT NULL DEFAULT 0,
                tool_calls_count   INTEGER NOT NULL DEFAULT 0,
                success_reason     TEXT,
                failure_reason     TEXT,
                started_at         TEXT NOT NULL,
                ended_at           TEXT,
                duration_sec       INTEGER
            )
        """)
        await db.commit()

        # Safe migration for existing databases that have the old schema
        existing = await db.execute_fetchall("PRAGMA table_info(call_sessions)")
        col_names = {r[1] for r in existing}
        migrations = [
            ("exercise_attempted", "ALTER TABLE call_sessions ADD COLUMN exercise_attempted INTEGER NOT NULL DEFAULT 0"),
            ("tool_calls_count",   "ALTER TABLE call_sessions ADD COLUMN tool_calls_count   INTEGER NOT NULL DEFAULT 0"),
            ("success_reason",     "ALTER TABLE call_sessions ADD COLUMN success_reason     TEXT"),
            ("failure_reason",     "ALTER TABLE call_sessions ADD COLUMN failure_reason     TEXT"),
            ("language",           "ALTER TABLE call_sessions ADD COLUMN language           TEXT NOT NULL DEFAULT 'od-IN'"),
        ]
        for col, sql in migrations:
            if col not in col_names:
                try:
                    await db.execute(sql)
                    await db.commit()
                    logger.info("Migration: added column %s to call_sessions", col)
                except Exception:
                    pass

    logger.info("call_sessions table ready.")


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------

async def start_session(
    session_id: str,
    user_id: str = "",
    call_type: str = "inbound",
    language: str = "od-IN",
) -> None:
    """Insert a new in-progress session row. Idempotent (INSERT OR IGNORE)."""
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            """INSERT OR IGNORE INTO call_sessions
               (session_id, user_id, call_type, language, outcome, started_at)
               VALUES (?, ?, ?, ?, 'in_progress', ?)""",
            (session_id, user_id, call_type, language, _now_iso()),
        )
        await db.commit()
    logger.info("Session started: %s call_type=%s", session_id, call_type)


async def increment_tool_calls(session_id: str) -> None:
    """Increment the tool-calls counter each time any tool is invoked."""
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            "UPDATE call_sessions SET tool_calls_count = tool_calls_count + 1 WHERE session_id = ?",
            (session_id,),
        )
        await db.commit()


async def mark_exercise_attempted(session_id: str) -> None:
    """Mark that the student reached and attempted an exercise → outcome = successful."""
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            """UPDATE call_sessions
               SET outcome            = 'successful',
                   exercise_attempted = 1,
                   success_reason     = 'exercise_tool_called'
               WHERE session_id = ?""",
            (session_id,),
        )
        await db.commit()
    logger.info("Exercise attempted — session marked successful: %s", session_id)


async def end_session(session_id: str) -> None:
    """
    Finalise the session: set ended_at, compute duration_sec, and
    flip any still-'in_progress' session to 'failed'.
    """
    now = _now_iso()
    async with aiosqlite.connect(_DB_PATH) as db:
        rows = await db.execute_fetchall(
            "SELECT started_at, outcome FROM call_sessions WHERE session_id = ?",
            (session_id,),
        )
        if not rows:
            logger.warning("end_session: unknown session_id %s — skipping", session_id)
            return
        started_at_str, current_outcome = rows[0]
        try:
            duration = int(
                (datetime.fromisoformat(now) - datetime.fromisoformat(started_at_str)).total_seconds()
            )
        except Exception:
            duration = None

        if current_outcome == "successful":
            final_outcome   = "successful"
            failure_reason  = None
        else:
            final_outcome   = "failed"
            failure_reason  = "ended_before_exercise"

        await db.execute(
            """UPDATE call_sessions
               SET ended_at = ?, duration_sec = ?, outcome = ?,
                   failure_reason = COALESCE(failure_reason, ?)
               WHERE session_id = ?""",
            (now, duration, final_outcome, failure_reason, session_id),
        )
        await db.commit()
    logger.info("Session ended: %s outcome=%s duration=%ss", session_id, final_outcome, duration)


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------

async def get_analytics() -> dict:
    """
    Return aggregate analytics. All numbers come from simple SQL aggregates —
    no LLM, no transcript parsing.
    """
    async with aiosqlite.connect(_DB_PATH) as db:
        totals = await db.execute_fetchall(
            """SELECT
                 COUNT(*)                                                       AS total,
                 SUM(CASE WHEN outcome = 'successful'  THEN 1 ELSE 0 END)      AS successful,
                 SUM(CASE WHEN outcome = 'failed'      THEN 1 ELSE 0 END)      AS failed,
                 SUM(CASE WHEN outcome = 'in_progress' THEN 1 ELSE 0 END)      AS in_progress,
                 AVG(CASE WHEN duration_sec IS NOT NULL THEN duration_sec END)  AS avg_duration,
                 AVG(CASE WHEN outcome='successful' AND duration_sec IS NOT NULL
                          THEN duration_sec END)                                AS avg_success_duration,
                 SUM(exercise_attempted)                                        AS exercises_attempted
               FROM call_sessions"""
        )
        row = totals[0] if totals else (0,) * 7
        total       = row[0] or 0
        successful  = row[1] or 0
        failed      = row[2] or 0
        in_progress = row[3] or 0
        avg_dur     = round(row[4]) if row[4] else None
        avg_suc_dur = round(row[5]) if row[5] else None
        exercises   = row[6] or 0
        rate        = round(successful / total * 100, 1) if total else 0.0

        daily_rows = await db.execute_fetchall(
            """SELECT DATE(started_at)                                       AS day,
                      COUNT(*)                                               AS total,
                      SUM(CASE WHEN outcome='successful' THEN 1 ELSE 0 END) AS successful,
                      SUM(CASE WHEN outcome='failed'     THEN 1 ELSE 0 END) AS failed
               FROM  call_sessions
               WHERE started_at >= DATE('now', '-13 days')
               GROUP BY day
               ORDER BY day ASC"""
        )
        daily_series = [
            {"date": r[0], "total": r[1], "successful": r[2], "failed": r[3]}
            for r in daily_rows
        ]

    return {
        "total_calls":            total,
        "successful_calls":       successful,
        "failed_calls":           failed,
        "in_progress_calls":      in_progress,
        "success_rate":           rate,
        "avg_duration_sec":       avg_dur,
        "avg_success_duration_sec": avg_suc_dur,
        "exercises_attempted":    exercises,
        "daily_series":           daily_series,
    }


async def get_recent_calls(limit: int = 10) -> list[dict]:
    """
    Return the last `limit` ended calls for the Recent Activity list.
    PRIVACY: user_id is anonymised to an 8-char hash; no transcript; no PII.
    """
    async with aiosqlite.connect(_DB_PATH) as db:
        rows = await db.execute_fetchall(
            """SELECT session_id, user_id, call_type, language,
                      outcome, exercise_attempted, success_reason, failure_reason,
                      started_at, duration_sec
               FROM call_sessions
               WHERE outcome != 'in_progress'
               ORDER BY started_at DESC
               LIMIT ?""",
            (limit,),
        )
    return [
        {
            "session_ref":         r[0][-6:].upper(),   # last 6 chars of room name — readable, not PII
            "user_ref":            _anon_id(r[1]) if r[1] else "ANON",
            "call_type":           r[2],
            "language":            r[3],
            "outcome":             r[4],
            "exercise_attempted":  bool(r[5]),
            "success_reason":      r[6],
            "failure_reason":      r[7],
            "started_at":          r[8],
            "duration_sec":        r[9],
        }
        for r in rows
    ]
