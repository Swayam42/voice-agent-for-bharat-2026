"""
scheduler.py — Background reminder scheduler for Mo Saathi (Day 6)
====================================================================
Runs as a background asyncio task inside the LiveKit agent process.
Every 60 seconds, it checks SQLite for due reminders and triggers
outbound calls via outbound_caller.py.

Features:
- Lightweight — uses asyncio.sleep(), no extra dependencies
- Persistent — reads from SQLite, so reminders survive agent restarts
- Safe — marks each reminder as "triggered" before calling to avoid duplicates
- Graceful — any per-reminder failure is caught and logged without crashing loop

Usage (in agent.py):
    import asyncio
    from scheduler import reminder_scheduler_loop
    asyncio.create_task(reminder_scheduler_loop())
"""

import asyncio
import logging

from database import get_user
from outbound_caller import place_outbound_call
from reminders import get_due_reminders, mark_reminder_status, handle_failed_call

logger = logging.getLogger("scheduler")

POLL_INTERVAL_SECONDS = 60  # check every 60 seconds


async def reminder_scheduler_loop() -> None:
    """
    Infinite background loop that polls for due reminders and fires calls.
    Should be started as an asyncio task at agent startup.
    """
    logger.info("Reminder scheduler started — polling every 60 seconds.")
    while True:
        try:
            await _process_due_reminders()
        except Exception as e:
            # Never crash the scheduler — just log and continue
            logger.error(f"Scheduler error: {e}")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def _process_due_reminders() -> None:
    """Check for due reminders and trigger outbound calls."""
    due = await get_due_reminders()
    if not due:
        return

    logger.info(f"Scheduler: {len(due)} reminder(s) due.")

    for reminder in due:
        reminder_id = reminder["id"]
        user_id = reminder["user_id"]
        linphone_username = reminder["linphone_username"]
        subject = reminder["subject"]

        # Mark as triggered FIRST to prevent duplicate calls on next poll
        await mark_reminder_status(reminder_id, "triggered")

        try:
            # Look up student name for personalised greeting
            profile = await get_user(user_id)
            student_name = (profile or {}).get("name") or "Student"

            logger.info(
                f"Scheduler: Triggering call for user={user_id} "
                f"name={student_name} subject={subject}"
            )

            result = await place_outbound_call(
                user_id=user_id,
                linphone_username=linphone_username,
                subject=subject,
                student_name=student_name,
            )

            if result.get("status") in ("dispatched", "dialing"):
                logger.info(
                    f"Scheduler: Call dispatched — room={result.get('room_name')}"
                )
            else:
                logger.error(f"Scheduler: Call failed — {result}")
                await handle_failed_call(reminder_id)

        except Exception as e:
            logger.error(f"Scheduler: Error processing reminder {reminder_id}: {e}")
            await handle_failed_call(reminder_id)

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(reminder_scheduler_loop())
    except KeyboardInterrupt:
        logger.info("Scheduler stopped.")
