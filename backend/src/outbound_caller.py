"""
outbound_caller.py -- Dispatcher for Mo Saathi outbound reminder calls
======================================================================
Creates a LiveKit room with reminder metadata and dispatches agent.py to it.
agent.py detects is_outbound=True and dials the SIP call itself via ctx.api.

See: https://docs.livekit.io/telephony/making-calls/outbound-calls/#agent-calls
"""

import json
import logging
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv

_BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(_BACKEND_DIR / ".env.local")
load_dotenv(_BACKEND_DIR / ".env")

logger = logging.getLogger("outbound_caller")

LIVEKIT_URL = os.environ.get("LIVEKIT_URL", "")
LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET", "")

# Empty string dispatches to the default unnamed agent (src/agent.py).
REMINDER_AGENT_NAME = ""


def _normalize_sip_destination(linphone_username: str) -> str:
    value = (linphone_username or "").strip()
    if value.startswith("sip:"):
        value = value[4:]
    if "@" in value:
        value = value.split("@")[0]
    return value.strip()


async def place_outbound_call(
    user_id: str,
    linphone_username: str,
    subject: str,
    student_name: str,
) -> dict:
    room_name = "outbound_" + user_id + "_" + uuid.uuid4().hex[:8]
    sip_call_to = _normalize_sip_destination(linphone_username)

    metadata = json.dumps({
        "sip_call_to": sip_call_to,
        "subject": subject,
        "student_name": student_name,
        "user_id": user_id,
        "linphone_username": linphone_username,
        "is_outbound": True,
    })

    logger.info("[SIP] Dialing linphone user %s for user=%s, subject=%s",
                linphone_username, user_id, subject)

    try:
        from livekit import api as lk_api

        lk = lk_api.LiveKitAPI(
            url=LIVEKIT_URL,
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET,
        )
        try:
            await lk.room.create_room(
                lk_api.CreateRoomRequest(name=room_name, metadata=metadata, empty_timeout=10 * 60)
            )
        finally:
            await lk.aclose()

        logger.info("[SIP] Call initiated: room=%s", room_name)
        return {"mode": "sip", "status": "dialing", "room_name": room_name, "sip_call_to": sip_call_to}

    except Exception as e:
        logger.error("[SIP] Failed to dispatch: %s", e)
        return {"mode": "sip", "status": "failed", "error": str(e)}
