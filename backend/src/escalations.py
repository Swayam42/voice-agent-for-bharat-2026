"""
escalations.py -- Human escalation management for Mo Saathi (Day 7)
===================================================================
Stores teacher-help requests in the shared SQLite database.

Each escalation has:
  - ref_id        -- ESC-XXXXXXXX the student can quote
  - summary       -- agent-written 2-4 sentence digest (NOT the raw transcript)
  - urgency       -- high / medium / low
  - status        -- open / resolved

Public API
----------
    init_escalations_table()    Create table if absent
    save_escalation(...)        Insert; returns ref_id string
    mark_email_sent(ref_id)     Update email_sent flag
    get_escalations(limit)      Return list[dict] newest-first
"""

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger("escalations")

_DB_DIR = Path(__file__).parent.parent / "data"
_DB_PATH = _DB_DIR / "mo_saathi.db"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_ref_id() -> str:
    return "ESC-" + uuid.uuid4().hex[:8].upper()


async def init_escalations_table() -> None:
    """Create escalations table if it does not exist."""
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS escalations (
                ref_id          TEXT PRIMARY KEY,
                user_id         TEXT NOT NULL,
                student_name    TEXT NOT NULL DEFAULT '',
                reason          TEXT NOT NULL,
                summary         TEXT NOT NULL,
                urgency         TEXT NOT NULL DEFAULT 'medium',
                language        TEXT NOT NULL DEFAULT 'odia',
                contact_method  TEXT NOT NULL DEFAULT 'phone_call',
                contact_info    TEXT NOT NULL DEFAULT '',
                status          TEXT NOT NULL DEFAULT 'open',
                email_sent      INTEGER NOT NULL DEFAULT 0,
                created_at      TEXT NOT NULL
            )
            """
        )
        await db.commit()
        # Safe migration for existing dev DB
        try:
            await db.execute("ALTER TABLE escalations ADD COLUMN contact_info TEXT NOT NULL DEFAULT ''")
            await db.commit()
            logger.info("Database migration: Added contact_info column to escalations table.")
        except Exception:
            pass
    logger.info("Escalations table ready.")


async def save_escalation(
    user_id: str,
    reason: str,
    summary: str,
    student_name: str = "",
    urgency: str = "medium",
    language: str = "odia",
    contact_method: str = "phone_call",
    contact_info: str = "",
) -> str:
    """Save a new escalation; returns the generated ref_id."""
    ref_id = _make_ref_id()
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO escalations
                (ref_id, user_id, student_name, reason, summary,
                 urgency, language, contact_method, contact_info, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)
            """,
            (
                ref_id, user_id, student_name, reason, summary,
                urgency, language, contact_method, contact_info, _now_iso(),
            ),
        )
        await db.commit()
    logger.info("Escalation saved: ref_id=%s user=%s urgency=%s", ref_id, user_id, urgency)
    return ref_id


async def mark_email_sent(ref_id: str) -> None:
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute("UPDATE escalations SET email_sent = 1 WHERE ref_id = ?", (ref_id,))
        await db.commit()


async def get_escalations(limit: int = 50) -> list[dict[str, Any]]:
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM escalations ORDER BY created_at DESC LIMIT ?", (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
    return [dict(r) for r in rows]
