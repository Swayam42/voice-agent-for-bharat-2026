# -*- coding: utf-8 -*-
"""
agent.py — Mo Saathi Voice Agent (Day 6: Outbound Reminder Calls)
=================================================================
Entry point for the LiveKit voice agent pipeline.

New in Day 6
------------
- Outbound study reminders (simulation mode — 100% free, no SIP account needed)
- Three new tools: schedule_study_reminder, cancel_study_reminder, list_my_reminders
- Background scheduler polling SQLite every 60s and triggering reminder calls
- Outbound call detection via room metadata (is_outbound flag)
- Personalised reminder opening script: "Hello {name}, this is Mo Saathi..."
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    ChatContext,
    ChatMessage,
    JobContext,
    JobProcess,
    RunContext,
    cli,
    llm,
    room_io,
    tokenize,
    function_tool,
)
from livekit.plugins import murf, noise_cancellation, openai, silero

from database import delete_user, get_user, init_db, save_user
from question_bank import get_random_question
from rag import load_knowledge_base, search
from reminders import cancel_reminder, init_reminders_table, list_reminders, save_reminder
from sarvam_stt import SarvamSTT

logger = logging.getLogger("agent")

load_dotenv()

# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """# IDENTITY
You are "Saathi", a friendly, patient, and highly encouraging educational AI learning companion for students in Odisha. You work for the students to make learning fun and accessible.

# IMPORTANT — GREETING RULE
The system has already greeted the user or personalised the greeting based on their profile.
DO NOT repeat any greeting, do NOT say "Namaskar", "Jay Jagannath", or introduce yourself again.
Dive straight into the conversation from where the student left off (if returning) or wait for their first question (if new).

# MEMORY & TOOLS
You have access to four tools:
1. lookup_student_profile — Call this at the start of EVERY session to recall facts about this student.
2. save_student_profile — Call this when you learn something new about the student (name, class, topics covered, mistakes). ALWAYS ask the student's permission before saving. Example: "Mu tumar naam save kari deba ki?" (Shall I remember your name?). If they say no, do NOT call this tool.
3. forget_me — Call this when the student explicitly asks to be forgotten. Confirm once before calling.
4. get_next_exercise — Whenever a student asks to be tested, wants practice questions, a quiz, MCQs, or revision exercises (e.g. "test me", "give me a question", "practice kariba"), you MUST call this tool. NEVER invent questions yourself. If the tool returns a question, translate it into Odia naturally. If the tool fails to find a question, gracefully and playfully apologize, and redirect the student to what you DO know (e.g., Class 9 and 10 Maths and Science).

# OBJECTIVES
Your goal is not only to answer questions, but to make the student curious enough to ask the next question.
A successful call achieves three things:
1. The student feels heard and understood.
2. A complex concept is explained simply and accurately.
3. After every explanation, ask ONE curiosity-driven follow-up question (e.g., "What do you think would happen if...", "Can you guess why...", "This reminds you of what?"). Avoid asking "Did you understand?".

# ACCURACY & KNOWLEDGE
You have broad knowledge of school subjects. Accuracy is more important than sounding confident.
If you are uncertain:
- Clearly say you are unsure.
- Never invent names, dates, numbers, historical events, or scientific facts.
- Never fabricate references.
- Never guess.

Your knowledge strictly stops at diagnosing issues or providing personal counseling.

# HOW TO EXPLAIN
Whenever explaining:
- Answer briefly.
- Explain why step-by-step.
- Use one everyday real-world example.
- Avoid textbook language.
- Never assume prior knowledge.
Remember what the student already understands during the conversation. Avoid repeating the same explanation unless asked. Build on previous answers.

# CRITICAL THINKING & EMPATHY
- If the user asks a common myth, clearly distinguish Fact, Myth, and Scientific evidence without making fun of the user.
- If the student sounds anxious (e.g., before an exam or feeling like a failure): FIRST encourage them and provide warm emotional support. Never ignore the emotional context. Then answer the academic question.

# LANGUAGE
Understand Odia, English, Hindi, and code-mixed conversations. Reply primarily in Odia.
Write ALL output using strictly Odia script characters.
Keep common technical words naturally transliterated into Odia script (e.g., write "Photosynthesis" as "ଫଟୋସିନ୍ଥେସିସ୍").
Only switch to full English if the user explicitly asks.
STRICT BAN: NEVER output any English, Hindi (Devanagari), or Bengali characters. Use ONLY Odia script characters.

# GUARDRAILS
1. Never shame a wrong answer. Always be supportive and encouraging.
2. Never claim or diagnose that a child has a learning disability.
3. For any diagnosis, medical, or harmful out-of-scope requests, you MUST explicitly decline and end with this exact escalation script: "ମୋର ସେହି ବିଷୟରେ ପରାମର୍ଶ ଦେବାର କ୍ଷମତା ନାହିଁ। ଦୟାକରି ଆପଣଙ୍କ ଶିକ୍ଷକ କିମ୍ବା ପିତାମାତାଙ୍କୁ ପଚାରନ୍ତୁ।"

# VOICE OPTIMIZATION
Plain text only. No markdown. No bullet lists.
Never speak in paragraphs. Prefer 8-15 word sentences.
Pause naturally. Avoid reading like a textbook. Sound like a friendly teacher. Ask one question at a time."""

# ---------------------------------------------------------------------------
# Outbound Call System Prompt (short, scripted, consent-first)
# ---------------------------------------------------------------------------

OUTBOUND_CALL_SYSTEM_PROMPT = """# IDENTITY
You are Mo Saathi, a friendly Odia learning companion making a scheduled reminder call.

# TASK
You placed this call because the student asked to be reminded to study.
Your opening is strictly scripted — say it word for word:
1. Introduce yourself.
2. State why you are calling (the reminder subject).
3. Offer to cancel future reminders if they wish.

# SCRIPTED OPENER (say this at the start):
"ନମସ୍କାର! ମୁଁ ମୋ ସାଥୀ। ଆପଣ ମୋତେ {subject} ପଢ଼ିବା ପାଇଁ ମନେ କରାଇ ଦେବାକୁ କହିଥିଲେ। ଯଦି ଆପଣ ଆଉ ଏହି ରିମାଇଣ୍ଡର ଚାହୁଁ ନାହାନ୍ତି, ଦୟାକରି ମୋତେ ବୋଲନ୍ତୁ।"

# AFTER THE OPENER:
- If the student wants to study now → help them with a question from the subject.
- If the student says stop reminders → call the cancel_study_reminder tool.
- Keep the call SHORT — under 3 minutes.
- If no response in 30 seconds, say goodbye and end.

# LANGUAGE
Reply primarily in Odia script. Keep sentences under 15 words. Plain text only, no markdown."""


# ---------------------------------------------------------------------------
# Agent Class
# ---------------------------------------------------------------------------

class Assistant(Agent):
    """
    Mo Saathi — the voice agent with memory and RAG.

    Each session creates a new Assistant instance. The user_id is injected
    at session start so all tool functions have access to the student's identity.
    """

    def __init__(self, user_id: str, instructions: str = SYSTEM_PROMPT) -> None:
        super().__init__(instructions=instructions)
        self._user_id = user_id

        # A smaller, faster model generates the filler phrase (acknowledgment)
        self._fast_llm = openai.LLM(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY", ""),
            model="google/gemini-3.5-flash-lite",
            extra_body={"max_tokens": 10},
        )
        self._fast_llm_prompt = llm.ChatMessage(
            role="system",
            content=[
                "Generate a highly natural, instantaneous 1-to-2 word conversational acknowledgment in pure Odia script based on the user's latest input.",
                "Act like a friendly human listening. Do not answer the question directly. Keep it to 1-2 words only.",
                "Use natural human sounds like 'ଆଚ୍ଛା...' (Acha), 'ହଁ...' (Yeah), 'ଦେଖିବା...' (Let's see), 'ବୁଝିଲି...' (Understood), or 'ଠିକ୍ ଅଛି...' (Alright).",
                "Do NOT use robotic phrases.",
            ],
        )

    # -----------------------------------------------------------------------
    # Pre-response acknowledgment (instant filler phrase)
    # -----------------------------------------------------------------------

    async def on_user_turn_completed(
        self, turn_ctx: ChatContext, new_message: ChatMessage,
    ) -> None:
        """
        Called immediately after the user finishes speaking.
        We fire a fast filler phrase ("ହଁ...", "ଆଚ୍ଛା...") while the main
        LLM is still thinking, so the student never hears dead silence.
        We also run RAG retrieval and inject relevant curriculum passages
        into the chat context before the main response.
        """
        # --- Filler phrase (non-blocking) ---
        fast_ctx = turn_ctx.copy(
            exclude_instructions=True,
            exclude_function_call=True,
        ).truncate(max_items=3)
        fast_ctx.items.insert(0, self._fast_llm_prompt)
        fast_ctx.items.append(new_message)
        self.session.say(
            self._fast_llm.chat(chat_ctx=fast_ctx).to_str_iterable(),
            add_to_chat_ctx=False,
        )

        # --- RAG retrieval ---
        query = new_message.text_content or ""
        if query.strip():
            rag_context = search(query, n_results=3)
            if rag_context:
                # Add curriculum context as a system message right before the LLM generates
                turn_ctx.add_message(
                    role="system",
                    content=rag_context,
                )
                logger.debug(f"[RAG] Injected context for query: '{query[:60]}'")

    # -----------------------------------------------------------------------
    # Tool 1: Look up student profile
    # -----------------------------------------------------------------------

    @function_tool
    async def lookup_student_profile(self, context: RunContext) -> str:
        """
        Look up the current student's stored profile from the database.
        Call this at the start of every session and whenever you need to
        recall facts about the student. Returns a summary of what is known,
        or confirms that this is a new student.
        """
        profile = await get_user(self._user_id)
        if profile is None:
            logger.info(f"[Tool] lookup_student_profile: no profile for '{self._user_id}'")
            return "This is a new student. No profile exists yet."

        topics = ", ".join(profile.get("topics_covered") or []) or "none recorded"
        mistakes = ", ".join(profile.get("repeated_mistakes") or []) or "none recorded"
        result = (
            f"Student profile found:\n"
            f"  Name: {profile.get('name', 'not set')}\n"
            f"  Class/Level: {profile.get('current_level', 'not set')}\n"
            f"  Language preference: {profile.get('language_preference', 'odia')}\n"
            f"  Topics covered: {topics}\n"
            f"  Repeated mistakes: {mistakes}\n"
            f"  Notes: {profile.get('notes', 'none')}\n"
            f"  Last interaction: {profile.get('last_interaction', 'unknown')}"
        )
        logger.info(f"[Tool] lookup_student_profile: returned profile for '{self._user_id}'")
        return result

    # -----------------------------------------------------------------------
    # Tool 2: Save student profile
    # -----------------------------------------------------------------------

    @function_tool
    async def save_student_profile(
        self,
        context: RunContext,
        name: str | None = None,
        current_level: str | None = None,
        topics_covered: list[str] | None = None,
        repeated_mistakes: list[str] | None = None,
        language_preference: str | None = None,
        notes: str | None = None,
    ) -> str:
        """
        Save or update facts about the current student.

        IMPORTANT: Only call this after the student has explicitly given
        permission to be remembered. Never call without consent.

        Arguments (all optional — only pass what you learned):
            name               — student's preferred name
            current_level      — e.g. "Class 9", "Class 10"
            topics_covered     — list of topics discussed this session
            repeated_mistakes  — list of misconceptions or errors observed
            language_preference — "odia", "english", or "mixed"
            notes              — any free-form notes about the student
        """
        kwargs = {}
        if name is not None:
            kwargs["name"] = name
        if current_level is not None:
            kwargs["current_level"] = current_level
        if topics_covered is not None:
            kwargs["topics_covered"] = topics_covered
        if repeated_mistakes is not None:
            kwargs["repeated_mistakes"] = repeated_mistakes
        if language_preference is not None:
            kwargs["language_preference"] = language_preference
        if notes is not None:
            kwargs["notes"] = notes

        if not kwargs:
            return "No fields provided to save. Please specify at least one piece of information."

        await save_user(self._user_id, **kwargs)
        saved_fields = ", ".join(kwargs.keys())
        logger.info(f"[Tool] save_student_profile: saved {saved_fields} for '{self._user_id}'")
        return f"Saved successfully: {saved_fields}. The student's profile has been updated."

    # -----------------------------------------------------------------------
    # Tool 3: Forget-me (delete all data)
    # -----------------------------------------------------------------------

    @function_tool
    async def forget_me(self, context: RunContext) -> str:
        """
        Permanently delete the current student's profile from the database.
        Use this when the student explicitly asks to be forgotten.
        Confirm once with the student before calling this tool.
        """
        deleted = await delete_user(self._user_id)
        if deleted:
            logger.info(f"[Tool] forget_me: deleted profile for '{self._user_id}'")
            return "Done. All your data has been permanently deleted. I will not remember you in future calls."
        else:
            logger.info(f"[Tool] forget_me: no profile found for '{self._user_id}'")
            return "You don't have a saved profile, so there is nothing to delete."

    # -----------------------------------------------------------------------
    # Tool 4: Get next exercise (practice questions)
    # -----------------------------------------------------------------------

    @function_tool
    async def get_next_exercise(
        self,
        context: RunContext,
        subject: str,
        class_level: str,
        topic: str | None = None
    ) -> str:
        """
        Fetch a practice question or quiz for the student.
        Use this whenever the student asks to be tested, wants a question,
        wants a quiz, or wants to practice.

        Arguments:
            subject      — e.g. "science", "maths", "history"
            class_level  — e.g. "Class 9", "Class 10"
            topic        — (optional) specific topic the student wants to practice
        """
        logger.info(f"[TOOL] get_next_exercise called subject={subject} class={class_level}")
        result = get_random_question(subject, class_level, topic)
        
        if result:
            return result["text"]
        else:
            return "TOOL_ERROR: No questions found for this topic. Naturally apologize and gently guide the student back to your main subjects (Class 9 and 10 Maths/Science)."

    # -----------------------------------------------------------------------
    # Tool 5: Schedule a study reminder
    # -----------------------------------------------------------------------

    @function_tool
    async def schedule_study_reminder(
        self,
        context: RunContext,
        subject: str,
        linphone_username: str,
        minutes_from_now: int,
    ) -> str:
        """
        Schedule a reminder call to the student to study a specific subject.
        Use this when the student asks to be reminded later to study or practice.

        Arguments:
            subject           — e.g. "Biology", "Maths Chapter 3"
            linphone_username — The student's Linphone username. IMPORTANT: If the speech-to-text captures this in Odia script (e.g. "ସ୍ୱୟମ ୪୨"), you MUST transliterate and convert it to a lowercase English alphanumeric string (e.g. "swayam42"). Linphone usernames only accept english letters and numbers.
            minutes_from_now  — how many minutes from now to trigger the call (minimum 1, max 1440 for 24h)

        ALWAYS ask the student's permission before scheduling. Example:
        "ମୁଁ ତୁମକୁ {minutes_from_now} ମିନିଟ ପରେ {subject} ପାଇଁ ଡାକ ଦେବି। ରାଜି ଅଛ?"
        Only call this tool after the student explicitly says yes.
        """
        import re
        from datetime import datetime, timedelta, timezone

        logger.info(f"[TOOL] schedule_study_reminder: subject={subject} linphone={linphone_username} mins={minutes_from_now}")

        # Basic validation for username
        if not linphone_username or len(linphone_username) < 3:
            return "That doesn't look like a valid Linphone username. Please provide a valid username."

        # Validate time range
        if minutes_from_now < 1:
            return "Please set a reminder for at least 1 minute from now."
        if minutes_from_now > 1440:
            return "I can only schedule reminders up to 24 hours (1440 minutes) in advance."

        remind_at = (datetime.now(timezone.utc) + timedelta(minutes=minutes_from_now)).isoformat()

        await save_reminder(
            user_id=self._user_id,
            linphone_username=linphone_username,
            subject=subject,
            remind_at=remind_at,
        )

        return (
            f"Reminder saved! I will call you in {minutes_from_now} minute(s) "
            f"to remind you to study {subject}. "
            f"If you change your mind, just tell me to cancel it."
        )

    # -----------------------------------------------------------------------
    # Tool 6: Cancel a study reminder
    # -----------------------------------------------------------------------

    @function_tool
    async def cancel_study_reminder(
        self,
        context: RunContext,
        subject: str,
    ) -> str:
        """
        Cancel an existing study reminder for a given subject.
        Use this when the student says they no longer want a reminder,
        or when they say 'stop reminders' during an outbound reminder call.

        Arguments:
            subject — the subject of the reminder to cancel (e.g. "Biology")
        """
        logger.info(f"[TOOL] cancel_study_reminder: user={self._user_id} subject={subject}")
        cancelled = await cancel_reminder(user_id=self._user_id, subject=subject)
        if cancelled:
            return f"Done! I have cancelled your {subject} reminder. You won't receive any more calls for this."
        return f"I couldn't find an active reminder for {subject}. Maybe it was already cancelled."

    # -----------------------------------------------------------------------
    # Tool 7: List current reminders
    # -----------------------------------------------------------------------

    @function_tool
    async def list_my_reminders(self, context: RunContext) -> str:
        """
        List all active study reminders for the current student.
        Call this when the student asks 'what reminders do I have?' or
        'when will you call me?' or 'show my reminders'.
        """
        logger.info(f"[TOOL] list_my_reminders: user={self._user_id}")
        reminders = await list_reminders(user_id=self._user_id)
        if not reminders:
            return "You don't have any active reminders right now."
        lines = []
        for r in reminders:
            lines.append(f"- {r['subject']} at {r['remind_at']} (status: {r['status']})")
        return "Your active reminders:\n" + "\n".join(lines)

# ---------------------------------------------------------------------------
# Agent server
# ---------------------------------------------------------------------------

server = AgentServer()


def prewarm(proc: JobProcess):
    """Pre-load VAD model and static data before the first session starts."""
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def my_agent(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}

    # -----------------------------------------------------------------------
    # Establish connection with LiveKit IMMEDIATELY.
    # -----------------------------------------------------------------------
    await ctx.connect()

    # Launch static data initialization
    import asyncio
    import json
    asyncio.create_task(init_db())
    asyncio.create_task(init_reminders_table())
    asyncio.create_task(load_knowledge_base())

    # -----------------------------------------------------------------------
    # Detect if this is an outbound reminder call BEFORE waiting for anyone.
    # Read from job metadata first (set by outbound_caller.py dispatch),
    # fall back to room metadata.
    # -----------------------------------------------------------------------
    room_metadata: dict = {}
    try:
        raw = ctx.job.metadata or getattr(ctx.room, "metadata", "") or ""
        if raw:
            room_metadata = json.loads(raw)
    except Exception:
        pass

    is_outbound: bool = bool(room_metadata.get("is_outbound", False))
    outbound_subject: str = room_metadata.get("subject", "your studies")
    outbound_student_name: str = room_metadata.get("student_name", "")
    outbound_user_id: str = room_metadata.get("user_id", "")
    sip_call_to: str = room_metadata.get("sip_call_to", "")

    # -----------------------------------------------------------------------
    # If outbound: dial the student's Linphone NOW (agent places the call).
    # Per LiveKit docs: wait_until_answered=True so session starts only
    # AFTER the student picks up — not while the phone is ringing.
    # -----------------------------------------------------------------------
    SIP_CALLEE_IDENTITY = "phone-student"
    if is_outbound and sip_call_to:
        trunk_id = os.environ.get("LIVEKIT_SIP_OUTBOUND_TRUNK_ID", "").strip()
        if not trunk_id:
            logger.error("LIVEKIT_SIP_OUTBOUND_TRUNK_ID not set — cannot make outbound call")
            ctx.shutdown()
            return
        logger.info("[Outbound] Dialing sip:%s via trunk %s", sip_call_to, trunk_id)
        from livekit import api as lk_api  # noqa: PLC0415
        try:
            await ctx.api.sip.create_sip_participant(
                lk_api.CreateSIPParticipantRequest(
                    room_name=ctx.room.name,
                    sip_trunk_id=trunk_id,
                    sip_call_to=sip_call_to,
                    participant_identity=SIP_CALLEE_IDENTITY,
                    participant_name=outbound_student_name or "Student",
                    wait_until_answered=True,  # Block until answered
                )
            )
        except lk_api.TwirpError as e:
            logger.error(
                "[Outbound] Call not answered: %s (SIP: %s)",
                e.message,
                e.metadata.get("sip_status", "?"),
            )
            ctx.shutdown()
            return
        except Exception as e:
            logger.error("[Outbound] Dial error: %s", e)
            ctx.shutdown()
            return
        logger.info("[Outbound] Call answered — waiting for SIP participant")
        participant = await ctx.wait_for_participant(identity=SIP_CALLEE_IDENTITY)
    else:
        # Normal web/browser call — wait for the frontend participant
        participant = await ctx.wait_for_participant()

    # -----------------------------------------------------------------------
    # Derive a stable user_id.
    # For outbound SIP: use the user_id embedded in dispatch metadata.
    # For web: use the participant identity set by the frontend.
    # -----------------------------------------------------------------------
    if is_outbound and outbound_user_id:
        user_id = outbound_user_id
    else:
        user_id = (
            participant.identity
            if participant and participant.identity
            else f"anonymous_{ctx.room.name}"
        )
    logger.info("Session started for user_id='%s' is_outbound=%s", user_id, is_outbound)

    # -----------------------------------------------------------------------
    # Load student profile and build a personalised greeting
    # -----------------------------------------------------------------------
    profile = await get_user(user_id)

    if is_outbound:
        # Outbound reminder call — use the scripted opener
        name = outbound_student_name or (profile or {}).get("name") or "Student"
        greeting = (
            f"ନମସ୍କାର {name}! ମୁଁ ମୋ ସାଥୀ। "
            f"ଆପଣ ମୋତେ {outbound_subject} ପଢ଼ିବା ପାଇଁ ମନେ କରାଇ ଦେବାକୁ କହିଥିଲେ। "
            f"ଏବେ ପ୍ରସ୍ତୁତ ଅଛନ୍ତି ନା?"
        )
        logger.info(f"Outbound call: name={name} subject={outbound_subject}")
        system_prompt = OUTBOUND_CALL_SYSTEM_PROMPT.replace("{subject}", outbound_subject)
    elif profile and profile.get("name"):
        # Returning student — greet by name and reference last interaction
        student_name = profile["name"]
        last_topics = profile.get("topics_covered") or []
        last_topic_str = last_topics[-1] if last_topics else None

        if last_topic_str:
            greeting = (
                f"ଜୟ ଜଗନ୍ନାଥ {student_name}! କେମିତି ଅଛ? "
                f"ଗତଥର ଆମେ {last_topic_str} ବିଷୟରେ ପଢୁଥିଲେ। "
                f"ଆଜି ସେଇଠୁ ଆରମ୍ଭ କରିବା ନା ନୂଆ କିଛି ଶିଖିବାକୁ ଇଚ୍ଛା ଅଛି?"
            )
        logger.info(f"Returning student: {student_name}")
        system_prompt = SYSTEM_PROMPT
    else:
        # New student
        greeting = "ନମସ୍କାର! ଜୟ ଜଗନ୍ନାଥ! ମୁଁ ତୁମର ସାଥୀ। ପ୍ରଥମେ, ତୁମ ନାମ କ'ଣ କହିବ କି?"
        logger.info("New student — using default greeting")
        system_prompt = SYSTEM_PROMPT

    # -----------------------------------------------------------------------
    # Build and start the session
    # -----------------------------------------------------------------------
    session = AgentSession(
        stt=SarvamSTT(language_code="od-IN"),
        llm=openai.LLM(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY", ""),
            model="google/gemini-3.5-flash-lite",
            extra_body={"max_tokens": 1000},
        ),
        tts=murf.TTS(
            voice="Anisha",
            locale="or-IN",
            model="FALCON",
            style="Conversational",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        ),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    # Use the correct system prompt depending on call type
    agent_instructions = system_prompt if is_outbound else SYSTEM_PROMPT

    from datetime import datetime, timezone, timedelta
    ist = timezone(timedelta(hours=5, minutes=30))
    ist_time = datetime.now(ist).strftime("%Y-%m-%d %I:%M %p IST")
    agent_instructions += f"\n\n# CURRENT TIME\nThe current date and time is {ist_time}. Use this to calculate minutes_from_now if the user requests a specific time."

    @session.on("metrics_collected")
    def _on_metrics_collected(metrics):
        if hasattr(metrics, "end_of_utterance_delay"):
            logger.info(
                f"Latency (end-of-speech → first audio): "
                f"{metrics.end_of_utterance_delay:.2f}s"
            )

    await session.start(
        agent=Assistant(user_id=user_id, instructions=agent_instructions),
        room=ctx.room,
    )

    # Speak the greeting and await it so the agent finishes before listening.
    # allow_interruptions=True lets the student cut in naturally mid-sentence.
    await session.say(greeting, allow_interruptions=True)


if __name__ == "__main__":
    cli.run_app(server)
