"""
outbound_caller.py — Outbound call dispatcher for Mo Saathi (Day 6)
====================================================================
Dispatches a reminder call to a student.

SIMULATION MODE (default — 100% free):
    No real phone call is made. Instead, a new LiveKit room is created
    and the agent is dispatched to it. The student can connect via the
    web UI using a special "answer reminder" token. This is fully
    demo-able on screen without any telephony provider.

REAL SIP MODE (Free Linphone Trunk):
    Activated by setting LIVEKIT_SIP_OUTBOUND_TRUNK_ID in .env.local.
    The LiveKit API dials the student's Linphone SIP URI.
    The agent joins the same room to handle the conversation.

Usage:
    from outbound_caller import place_outbound_call
    result = await place_outbound_call(user_id, linphone_username, subject, student_name)
"""

import logging
import os
import uuid

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("outbound_caller")

LIVEKIT_URL = os.environ.get("LIVEKIT_URL", "")
LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET", "")
SIP_TRUNK_ID = os.environ.get("LIVEKIT_SIP_OUTBOUND_TRUNK_ID", "")
SIP_CALLER_ID = os.environ.get("LIVEKIT_SIP_CALLER_ID", "")


async def place_outbound_call(
    user_id: str,
    linphone_username: str,
    subject: str,
    student_name: str,
) -> dict:
    """
    Dispatch an outbound reminder call.

    In simulation mode (no SIP trunk configured):
        - Creates a new LiveKit room named "outbound_{user_id}_{uuid}"
        - Dispatches the agent to that room with outbound metadata
        - Returns the room name so the frontend (or test script) can connect

    In SIP mode (LIVEKIT_SIP_TRUNK_ID set in env):
        - Dials the student's phone via LiveKit SIP API
        - Agent joins the same room automatically
    """
    room_name = f"outbound_{user_id}_{uuid.uuid4().hex[:8]}"
    metadata = f'{{"subject": "{subject}", "student_name": "{student_name}", "user_id": "{user_id}", "linphone_username": "{linphone_username}", "is_outbound": true}}'

    if not SIP_TRUNK_ID:
        # ----------------------------------------------------------------
        # SIMULATION MODE — dispatch agent to a browser-accessible room.
        # ----------------------------------------------------------------
        logger.info(
            f"[SIMULATION] Dispatching reminder call to room={room_name} "
            f"for user={user_id}, subject={subject}"
        )
        try:
            from livekit import api as lk_api

            lk = lk_api.LiveKitAPI(
                url=LIVEKIT_URL,
                api_key=LIVEKIT_API_KEY,
                api_secret=LIVEKIT_API_SECRET,
            )

            # Create the room first so the agent has somewhere to join
            await lk.room.create_room(
                lk_api.CreateRoomRequest(name=room_name, metadata=metadata)
            )
            logger.info(f"[SIMULATION] Created room: {room_name}")

            # Dispatch the agent job to this room
            await lk.agent.create_job(
                lk_api.CreateJobRequest(
                    room=lk_api.CreateJobRequestRoom(room_name=room_name),
                    metadata=metadata,
                )
            )
            logger.info(f"[SIMULATION] Agent dispatched to room: {room_name}")

            return {
                "mode": "simulation",
                "status": "dispatched",
                "room_name": room_name,
                "connect_url": f"{LIVEKIT_URL}?room={room_name}",
            }
        except Exception as e:
            logger.error(f"[SIMULATION] Failed to dispatch agent: {e}")
            return {"mode": "simulation", "status": "failed", "error": str(e)}

    else:
        # ----------------------------------------------------------------
        # REAL SIP MODE — dial the student's Linphone app.
        # ----------------------------------------------------------------
        logger.info(
            f"[SIP] Dialing linphone user {linphone_username} for user={user_id}, subject={subject}"
        )
        try:
            from livekit import api as lk_api

            lk = lk_api.LiveKitAPI(
                url=LIVEKIT_URL,
                api_key=LIVEKIT_API_KEY,
                api_secret=LIVEKIT_API_SECRET,
            )

            # Create room with outbound metadata so the agent knows context
            await lk.room.create_room(
                lk_api.CreateRoomRequest(name=room_name, metadata=metadata)
            )

            # Create SIP participant — this dials the student's Linphone
            # LiveKit requires just the user/number, not the full domain URI.
            clean_username = linphone_username.replace("sip:", "").split("@")[0]
            sip_user = f"sip:{clean_username}"
            
            await lk.sip.create_sip_participant(
                lk_api.CreateSIPParticipantRequest(
                    sip_trunk_id=SIP_TRUNK_ID,
                    sip_call_to=sip_user,
                    sip_number=SIP_CALLER_ID or sip_user,
                    display_name="Mo Saathi (AI Tutor)",
                    room_name=room_name,
                    participant_identity=f"phone_{user_id}",
                    participant_name=student_name,
                )
            )

            # Dispatch the agent to the same room
            await lk.agent_dispatch.create_dispatch(
                lk_api.CreateAgentDispatchRequest(
                    agent_name=os.environ.get("AGENT_NAME", ""),
                    room=room_name,
                    metadata=metadata,
                )
            )

            logger.info(f"[SIP] Call initiated: room={room_name}")
            return {"mode": "sip", "status": "dialing", "room_name": room_name}

        except Exception as e:
            logger.error(f"[SIP] Failed to initiate call: {e}")
            return {"mode": "sip", "status": "failed", "error": str(e)}
