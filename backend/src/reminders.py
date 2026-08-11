"""
reminders.py — Study reminder storage for Mo Saathi (Day 6)
=============================================================
Stores scheduled study reminders in SQLite. These are used by
the background scheduler to trigger outbound reminder calls.

Schema
------
reminders table:
    id                INTEGER  PRIMARY KEY AUTOINCREMENT
    user_id           TEXT     — links to users table
    linphone_username TEXT     — e.g. "student123"
    subject           TEXT     — e.g. "Biology", "Maths Chapter 5"
    remind_at         TEXT     — ISO 8601 UTC timestamp (when to call)
    enabled           INTEGER  — 1 = active, 0 = cancelled
    status            TEXT     — "pending" | "triggered" | "missed" | "failed"
    retry_count       INTEGER  — number of times we tried to call
    created_at        TEXT     — ISO 8601 timestamp

Public API
----------
    init_reminders_table()                 → Creates table if not exists
    save_reminder(user_id, ...)            → Insert a new reminder
    list_reminders(user_id)               → Return all active reminders for user
    cancel_reminder(user_id, subject)     → Disable matching reminder
    get_due_reminders()                   → Return reminders due right now
    mark_reminder_status(id, status)      → Update reminder status
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger("reminders")

_DB_DIR = Path(__file__).parent.parent / "data"
_DB_PATH = _DB_DIR / "mo_saathi.db"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def init_reminders_table() -> None:
    """Create the reminders table. Drops existing table for schema upgrade during dev."""
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(_DB_PATH) as db:
        # Drop table to ensure clean schema migration for Linphone update
        await db.execute("DROP TABLE IF EXISTS reminders")
        await db.execute(
            """
            CREATE TABLE reminders (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id           TEXT NOT NULL,
                linphone_username TEXT NOT NULL,
                subject           TEXT NOT NULL,
                remind_at         TEXT NOT NULL,
                enabled           INTEGER NOT NULL DEFAULT 1,
                status            TEXT NOT NULL DEFAULT 'pending',
                retry_count       INTEGER NOT NULL DEFAULT 0,
                created_at        TEXT NOT NULL
            )
            """
        )
        await db.commit()
    logger.info("Reminders table ready (re-initialized for Linphone).")


async def save_reminder(
    user_id: str,
    linphone_username: str,
    subject: str,
    remind_at: str,
) -> dict[str, Any]:
    """
    Insert a new reminder for a student.
    remind_at must be an ISO 8601 UTC timestamp.
    """
    now = _now_iso()
    async with aiosqlite.connect(_DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO reminders (user_id, linphone_username, subject, remind_at, enabled, status, retry_count, created_at)
            VALUES (?, ?, ?, ?, 1, 'pending', 0, ?)
            """,
            (user_id, linphone_username, subject, remind_at, now),
        )
        await db.commit()
        row_id = cursor.lastrowid

    logger.info(f"Reminder saved: id={row_id} user={user_id} subject={subject} at={remind_at}")
    return {
        "id": row_id,
        "user_id": user_id,
        "linphone_username": linphone_username,
        "subject": subject,
        "remind_at": remind_at,
        "status": "pending",
    }


async def list_reminders(user_id: str) -> list[dict[str, Any]]:
    """Return all active (enabled) reminders for this student."""
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM reminders WHERE user_id = ? AND enabled = 1 ORDER BY remind_at ASC",
            (user_id,),
        ) as cursor:
            rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def cancel_reminder(user_id: str, subject: str) -> bool:
    """Disable the most recent active reminder for this subject."""
    async with aiosqlite.connect(_DB_PATH) as db:
        cursor = await db.execute(
            """
            UPDATE reminders SET enabled = 0
            WHERE user_id = ? AND subject LIKE ? AND enabled = 1
            """,
            (user_id, f"%{subject}%"),
        )
        await db.commit()
        cancelled = cursor.rowcount > 0

    if cancelled:
        logger.info(f"Cancelled reminder: user={user_id} subject={subject}")
    return cancelled


async def get_due_reminders() -> list[dict[str, Any]]:
    """
    Return all pending reminders whose remind_at time has passed.
    Used by the scheduler to trigger outbound calls.
    """
    now = _now_iso()
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM reminders
            WHERE enabled = 1 AND status = 'pending' AND remind_at <= ?
            """,
            (now,),
        ) as cursor:
            rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def mark_reminder_status(reminder_id: int, status: str) -> None:
    """Update the status of a reminder (triggered, missed, failed)."""
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            "UPDATE reminders SET status = ? WHERE id = ?",
            (status, reminder_id),
        )
        await db.commit()
async def handle_failed_call(reminder_id: int) -> None:
    """
    Handle outcomes like no answer, busy, or SIP failure.
    Retry rule: Retry up to 2 times, waiting 5 minutes each time.
    """
    from datetime import datetime, timedelta, timezone

    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT retry_count FROM reminders WHERE id = ?", (reminder_id,)) as cursor:
            row = await cursor.fetchone()

        if not row:
            return

        retry_count = row["retry_count"]
        if retry_count < 2:
            new_time = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
            await db.execute(
                "UPDATE reminders SET status = 'pending', remind_at = ?, retry_count = retry_count + 1 WHERE id = ?",
                (new_time, reminder_id),
            )
            logger.info(f"Reminder {reminder_id} failed. Retrying in 5 mins (Attempt {retry_count + 1}/2).")
        else:
            await db.execute("UPDATE reminders SET status = 'failed' WHERE id = ?", (reminder_id,))
            logger.warning(f"Reminder {reminder_id} failed 3 times. Giving up.")

        await db.commit()
