"""
database.py — Persistent user memory for Mo Saathi
====================================================
Stores student profiles in a local SQLite database so the agent can remember
students across calls. Uses aiosqlite for async-safe reads and writes.

Schema
------
users table:
    user_id            TEXT  PRIMARY KEY  — stable identity (from LiveKit token)
    name               TEXT              — student's preferred name
    language_preference TEXT             — "odia" | "english" | "mixed"
    current_level      TEXT              — e.g. "Class 9", "Class 10"
    topics_covered     TEXT              — JSON-encoded list of topics discussed
    repeated_mistakes  TEXT              — JSON-encoded list of common errors
    notes              TEXT              — free-form notes from agent
    last_interaction   TEXT              — ISO 8601 timestamp
    created_at         TEXT              — ISO 8601 timestamp

Public API
----------
    init_db()                  → Creates tables if they don't exist
    get_user(user_id)          → Returns dict or None
    save_user(user_id, **kw)   → Upsert a user record
    delete_user(user_id)       → Wipes a student's data (forget-me)
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger("database")

# ---------------------------------------------------------------------------
# Database location — lives in backend/data/ so it persists across restarts.
# The directory is created automatically if it doesn't exist.
# ---------------------------------------------------------------------------
_DB_DIR = Path(__file__).parent.parent / "data"
_DB_PATH = _DB_DIR / "mo_saathi.db"


def _now_iso() -> str:
    """Return current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


async def init_db() -> None:
    """
    Create the database directory and tables if they don't already exist.
    Call once at agent startup before any other DB function.
    """
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id             TEXT PRIMARY KEY,
                name                TEXT,
                language_preference TEXT DEFAULT 'odia',
                current_level       TEXT,
                topics_covered      TEXT DEFAULT '[]',
                repeated_mistakes   TEXT DEFAULT '[]',
                notes               TEXT,
                last_interaction    TEXT,
                created_at          TEXT
            )
            """
        )
        await db.commit()
    logger.info(f"Database ready at {_DB_PATH}")


async def get_user(user_id: str) -> dict[str, Any] | None:
    """
    Look up a student by their stable user_id.

    Returns a dict with all fields if found, or None if this is a new student.
    JSON fields (topics_covered, repeated_mistakes) are decoded into Python lists.
    """
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()

    if row is None:
        return None

    data = dict(row)
    # Decode JSON-encoded list fields
    data["topics_covered"] = json.loads(data.get("topics_covered") or "[]")
    data["repeated_mistakes"] = json.loads(data.get("repeated_mistakes") or "[]")
    logger.info(f"Loaded profile for user '{user_id}' (name={data.get('name')})")
    return data


async def save_user(user_id: str, **kwargs: Any) -> dict[str, Any]:
    """
    Upsert a student profile. Pass any subset of fields as keyword arguments.

    List fields (topics_covered, repeated_mistakes) are accepted as Python lists
    and automatically JSON-encoded for storage.

    Example:
        await save_user(
            "abc123",
            name="Ramesh",
            current_level="Class 9",
            topics_covered=["Photosynthesis", "Newton's Laws"],
        )
    """
    # Fetch existing record so we can merge list fields rather than overwrite
    existing = await get_user(user_id) or {}

    # Merge list fields (append new items, deduplicate)
    for list_field in ("topics_covered", "repeated_mistakes"):
        if list_field in kwargs and isinstance(kwargs[list_field], list):
            existing_list = existing.get(list_field, [])
            merged = list(dict.fromkeys(existing_list + kwargs[list_field]))
            kwargs[list_field] = json.dumps(merged)
        elif list_field in kwargs and isinstance(kwargs[list_field], str):
            # Already JSON-encoded, leave as-is
            pass

    now = _now_iso()
    kwargs["last_interaction"] = now

    if not existing:
        # Brand-new student — set created_at
        kwargs.setdefault("created_at", now)
        kwargs.setdefault("language_preference", "odia")
        kwargs.setdefault("topics_covered", "[]")
        kwargs.setdefault("repeated_mistakes", "[]")

    # Build dynamic UPSERT
    fields = {"user_id": user_id, **kwargs}
    columns = ", ".join(fields.keys())
    placeholders = ", ".join("?" for _ in fields)
    updates = ", ".join(
        f"{col} = excluded.{col}" for col in fields if col != "user_id"
    )

    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            f"""
            INSERT INTO users ({columns})
            VALUES ({placeholders})
            ON CONFLICT(user_id) DO UPDATE SET {updates}
            """,
            list(fields.values()),
        )
        await db.commit()

    logger.info(f"Saved profile for user '{user_id}' — fields: {list(kwargs.keys())}")
    # Return the full updated record
    return await get_user(user_id) or fields


async def delete_user(user_id: str) -> bool:
    """
    Permanently delete a student's profile (the 'forget-me' request).

    Returns True if a record was deleted, False if the user wasn't found.
    """
    async with aiosqlite.connect(_DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM users WHERE user_id = ?", (user_id,)
        )
        await db.commit()
        deleted = cursor.rowcount > 0

    if deleted:
        logger.info(f"Deleted profile for user '{user_id}' (forget-me)")
    else:
        logger.info(f"No profile found for user '{user_id}' — nothing to delete")
    return deleted
