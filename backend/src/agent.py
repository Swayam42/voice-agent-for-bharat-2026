# -*- coding: utf-8 -*-
"""
agent.py — Mo Saathi Voice Agent (Day 9: Science Specialist Handoff)
==========================================================
Entry point for the LiveKit voice agent pipeline.

New in Day 9
------------
- ScienceSpecialist agent: a dedicated Physics/Chemistry/Biology expert for
  Class 9 and 10 students in Odisha.
- transfer_to_science_specialist tool: Mo Saathi hands off to the specialist
  when the student needs deep subject-level help beyond general guidance.
- Full conversation context is passed at handoff so the student never has to
  repeat themselves.
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
from livekit.plugins import google, murf, noise_cancellation, openai, silero

from database import delete_user, get_user, init_db, save_user
from escalation_mailer import send_escalation_email
from escalations import init_escalations_table as init_escalations_table_fn
from escalations import mark_email_sent, save_escalation
from question_bank import get_random_question
from rag import load_knowledge_base, search
from reminders import cancel_reminder, init_reminders_table, list_reminders, save_reminder
from call_sessions import (
    init_sessions_table,
    start_session,
    mark_exercise_attempted,
    increment_tool_calls,
    end_session,
)
from sarvam_stt import SarvamSTT

logger = logging.getLogger("agent")

load_dotenv()

# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """# IDENTITY
You are "Saathi", a friendly educational AI learning companion for students in Odisha.

# IMPORTANT — GREETING RULE
Do NOT repeat greetings, say "Namaskar", or introduce yourself again. Dive straight into the conversation.

# MEMORY & TOOLS
1. lookup_student_profile — Call at start to recall facts.
2. save_student_profile — Call when you learn new facts. Ask permission first.
3. get_next_exercise — Call when a student wants practice/quiz.
4. schedule_study_reminder — Manage reminders.
5. create_escalation — Call ONLY if student expresses emotional distress OR fails to understand after 3+ explanations. Ask permission first.
6. transfer_to_science_specialist — Call when the student needs a DEEP explanation of Physics, Chemistry, or Biology (Class 9 or 10). Before calling, say: "ଏହି ପ୍ରଶ୍ନ ପାଇଁ ମୁଁ ତୁମ୍ଭକୁ ଆମ ବିଜ୍ଞାନ ବିଶେଷଜ୍ଞ 'ବିଜ୍ଞାନ ସାଥୀ' ପାଖକୁ ଯୋଡ଼ୁଛି।"

# OBJECTIVES & EXPLAINING
1. Make student feel heard.
2. Explain briefly, step-by-step. Use 1 real-world example. Do NOT guess or hallucinate facts.
3. Ask ONE follow-up question.

# LANGUAGE
- Speak naturally in Odia.
- If using English technical words, write them in English alphabet, but NEVER put English translations in brackets. 
- Do not repeat words in multiple languages (e.g., do not say "ବଳ (Force)"). Pick one language for the word and stick to it.
- Plain text only. Keep sentences under 15 words. Pause naturally.

# GUARDRAILS
- Never shame a wrong answer.
- For medical/harmful/out-of-scope requests, decline with: "ମୋର ସେହି ବିଷୟରେ ପରାମର୍ଶ ଦେବାର କ୍ଷମତା ନାହିଁ। ଦୟାକରି ଆପଣଙ୍କ ଶିକ୍ଷକ କିମ୍ବା ପିତାମାତାଙ୍କୁ ପଚାରନ୍ତୁ।"
"""

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
# Science Specialist Prompt (Day 9)
# ---------------------------------------------------------------------------

SCIENCE_SPECIALIST_PROMPT = """# IDENTITY
You are "Vigyan Saathi" (ବିଜ୍ଞାନ ସାଥୀ), an expert Science teacher specialising in
Class 9 and Class 10 Physics, Chemistry, and Biology for Odia-medium students.
Mo Saathi transferred this student to you because they need in-depth science help.

# YOUR ONE JOB
Explain science concepts deeply, clearly, and accurately.
If asked to do anything outside science (Maths, History, scheduling, etc.),
politely say: "ସେ ବିଷୟ ପାଇଁ ଦୟାକରି ମୋ ସାଥୀ ସହ କଥା ହୁଅ। ମୁଁ କେବଳ ବିଜ୍ଞାନ ପ୍ରଶ୍ନ ସାହାଯ୍ୟ କରିବି।"

# HOW TO EXPLAIN
1. Greet the student warmly and acknowledge what they were working on.
2. Explain the concept step-by-step with a real-world Odia context example.
   (e.g. "ଗ୍ରୀଷ୍ମ ଋତୁରେ ଜଳ ଗ୍ଲାସ ଥଣ୍ଡା ହୋଇଯାଏ" for condensation)
3. Ask ONE targeted question to check understanding.
4. If the student is wrong, encourage first, then guide gently.
5. Never shame a wrong answer.

# SCOPE — STRICTLY THESE TOPICS:
- Physics: Motion, Force, Laws of Motion, Gravitation, Work & Energy, Sound, Light, Electricity, Magnetic Effects
- Chemistry: Matter, Atoms & Molecules, Chemical Reactions, Acids/Bases/Salts, Metals & Non-metals, Carbon Compounds
- Biology: Cell, Tissues, Life Processes, Reproduction, Heredity, Environment & Ecosystem

# LANGUAGE
- Speak naturally in Odia.
- If using English technical words, write them in English alphabet, but NEVER put English translations in brackets. 
- Do not repeat words in multiple languages (e.g., do not say "ବଳ (Force)"). Pick one language for the word and stick to it.
- Plain text only. Keep sentences under 15 words. Pause naturally."""


# ---------------------------------------------------------------------------
# Science Specialist Agent (Day 9)
# ---------------------------------------------------------------------------

class ScienceSpecialist(Agent):
    """
    Vigyan Saathi — a focused Physics/Chemistry/Biology expert.
    Activated via handoff from the main Assistant when deep science help is needed.
    Inherits full chat context so the student does not have to repeat themselves.
    """

    def __init__(self, chat_ctx: ChatContext | None = None) -> None:
        super().__init__(
            instructions=SCIENCE_SPECIALIST_PROMPT,
            chat_ctx=chat_ctx,
            tts=murf.TTS(
                voice="Samar",             # Different Murf voice to signal the handoff
                locale="or-IN",
                model="FALCON",
                style="Conversational",
                tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
                text_pacing=True,
            ),
        )

    async def on_enter(self) -> None:
        """Introduce Vigyan Saathi the moment it takes over."""
        await self.session.generate_reply(
            instructions=(
                "Introduce yourself as Vigyan Saathi (ବିଜ୍ଞାନ ସାଥୀ), "
                "Mo Saathi's Science specialist. Warmly acknowledge the topic "
                "the student was discussing and offer to go deeper. "
                "Keep it to 2-3 sentences in Odia script."
            )
        )


# ---------------------------------------------------------------------------
# Agent Class
# ---------------------------------------------------------------------------

class Assistant(Agent):
    """
    Mo Saathi — the voice agent with memory and RAG.

    Each session creates a new Assistant instance. The user_id is injected
    at session start so all tool functions have access to the student's identity.
    """

    def __init__(self, user_id: str, instructions: str = SYSTEM_PROMPT, room_name: str = "") -> None:
        super().__init__(instructions=instructions)
        self._user_id = user_id
        self._room_name = room_name

        # A smaller, faster model generates the filler phrase (acknowledgment)
        self._fast_llm = google.LLM(
            model="gemini-3.1-flash-lite",
            api_key=os.environ.get("GOOGLE_API_KEY", ""),
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

        # --- Chat context limitation ---
        # Keep only the last 6 ChatMessages to save prompt tokens.
        # Must check isinstance since turn_ctx.items can contain AgentConfigUpdate etc.
        if len(turn_ctx.items) > 10:
            chat_items = [m for m in turn_ctx.items if isinstance(m, ChatMessage)]
            other_items = [m for m in turn_ctx.items if not isinstance(m, ChatMessage)]
            system_chats = [m for m in chat_items if m.role == "system"]
            recent_chats = [m for m in chat_items if m.role != "system"][-6:]
            turn_ctx.items = other_items + system_chats + recent_chats

        # --- RAG retrieval ---
        query = new_message.text_content or ""
        if len(query.split()) > 5:  # Only RAG on substantive questions (5+ words)
            rag_context = search(query, n_results=1)
            if rag_context:
                rag_context = rag_context[:400]  # Truncate to ~400 chars
                # Inject directly into the user message instead of appending a system message.
                # This prevents Gemini 400 errors (function call must follow user/function turn).
                if isinstance(new_message.content, str):
                    new_message.content += f"\n\n[Context: {rag_context}]"
                elif isinstance(new_message.content, list):
                    new_message.content.append(f"\n\n[Context: {rag_context}]")
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

        # Get last topic and last mistake to keep prompt short
        topics_list = profile.get("topics_covered") or []
        last_topic = topics_list[-1] if topics_list else "None"
        
        mistakes_list = profile.get("repeated_mistakes") or []
        last_mistake = mistakes_list[-1] if mistakes_list else "None"

        result = (
            f"Name: {profile.get('name', 'not set')}\n"
            f"Class: {profile.get('current_level', 'not set')}\n"
            f"Last Topic: {last_topic}\n"
            f"Last Mistake: {last_mistake}\n"
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

        # Track every tool invocation for analytics
        import asyncio as _asyncio
        _asyncio.create_task(increment_tool_calls(self._room_name))

        if result:
            # Mark session successful — student reached an exercise (Day 8)
            _asyncio.create_task(mark_exercise_attempted(self._room_name))
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

    # -----------------------------------------------------------------------
    # Tool 8: Create human escalation (Day 7)
    # -----------------------------------------------------------------------

    @function_tool
    async def create_escalation(
        self,
        context: RunContext,
        reason: str,
        summary: str,
        urgency: str,
        contact_method: str,
        contact_info: str,
        consent_obtained: bool,
    ) -> str:
        """
        Request human teacher help when the student needs support beyond AI.

        WHEN TO USE — Two situations only:
        1. The student is emotionally distressed: expressing hopelessness, wanting
           to give up, crying, or severe exam anxiety.
        2. The student cannot understand the same concept after 3+ of your
           explanations (repeated academic failure on the same topic).

        CONSENT WORKFLOW (follow every time, in order):
          Step 1: Tell the student what you will share:
                  their name, today's topic/situation, and a brief summary.
          Step 2: Ask explicitly for their contact details (e.g. phone number or email)
                  so the teacher can contact them back.
          Step 3: Ask explicitly: "Mu apananka naam, contact info (e.g. {contact_info}) aau
                  aajira session summary eka teacher ku pathaibi. Raji achanti?"
          Step 4: If they say YES -> call this tool with consent_obtained=True.
          Step 5: If they say NO  -> do NOT call this tool. Respect their choice.

        Arguments:
            reason           Brief escalation reason, max 80 chars.
                             E.g. "Student expressed exam hopelessness"
            summary          2-4 sentence digest: who needs help, what happened,
                             what the agent already tried, urgency context.
                             NEVER include passwords, OTPs, or private data.
            urgency          One of: "high" (acute distress), "medium" (academic
                             difficulty), "low" (general concern).
            contact_method   Student's preferred follow-up: "phone_call",
                             "email", or "visit".
            contact_info     The student's phone number or email address to reach them at.
            consent_obtained Must be True. If the student has NOT said yes,
                             do NOT call this tool at all.
        """
        if not consent_obtained:
            logger.warning("[Tool] create_escalation called without consent -- blocked.")
            return (
                "Escalation NOT created: the student did not give consent. "
                "Do not call this tool without explicit permission."
            )

        # Enrich with stored profile
        profile = await get_user(self._user_id)
        student_name = (profile or {}).get("name", "")
        language = (profile or {}).get("language_preference", "odia")

        ref_id = await save_escalation(
            user_id=self._user_id,
            reason=reason,
            summary=summary,
            student_name=student_name,
            urgency=urgency,
            language=language,
            contact_method=contact_method,
            contact_info=contact_info,
        )

        email_sent = await send_escalation_email(
            ref_id=ref_id,
            student_name=student_name,
            reason=reason,
            summary=summary,
            urgency=urgency,
            language=language,
            contact_method=contact_method,
            contact_info=contact_info,
        )
        if email_sent:
            await mark_email_sent(ref_id)

        logger.info(
            "[Tool] create_escalation: ref=%s urgency=%s email_sent=%s",
            ref_id, urgency, email_sent,
        )
        return (
            f"Escalation created. Reference ID: {ref_id}. "
            f"A teacher has been notified with a summary of today's session. "
            + ("An email notification was also sent. " if email_sent else "")
            + f"You will be contacted at {contact_info} via {contact_method.replace('_', ' ')} soon. "
            f"Please remember your reference number: {ref_id}. "
            f"A human will review this and get back to you — usually within one school day."
        )

    # -----------------------------------------------------------------------
    # Tool 9: Transfer to Science Specialist (Day 9)
    # -----------------------------------------------------------------------

    @function_tool
    async def transfer_to_science_specialist(
        self, context: RunContext
    ) -> tuple[Agent, str]:
        """
        Hand the student off to the Science Specialist (Vigyan Saathi).

        WHEN TO USE — Transfer ONLY when:
        1. The student asks for a deep Physics, Chemistry, or Biology explanation
           that goes beyond a brief overview (e.g. Newton's laws, atomic structure,
           photosynthesis, chemical equations).
        2. The student is confused after one attempt and needs expert-level guidance
           on a specific science concept.
        3. The student explicitly asks "can I talk to a science expert" or similar.

        Do NOT transfer for:
        - Simple one-line answers to general questions.
        - Maths, History, or any non-science topic.
        - Scheduling reminders or profile updates.

        Before calling this tool, always say in Odia:
        "ଏହି ପ୍ରଶ୍ନ ପାଇଁ ମୁଁ ତୁମ୍ଭକୁ ଆମ ବିଜ୍ଞାନ ବିଶେଷଜ୍ଞ 'ବିଜ୍ଞାନ ସାଥୀ' ପାଖକୁ ଯୋଡ଼ୁଛି।"
        """
        science_agent = ScienceSpecialist(
            chat_ctx=self.chat_ctx.copy(exclude_instructions=True)
        )
        logger.info("[Tool] transfer_to_science_specialist: handing off to ScienceSpecialist")
        import asyncio as _asyncio
        _asyncio.create_task(increment_tool_calls(self._room_name))
        return science_agent, "ବିଜ୍ଞାନ ସାଥୀ ସହ ଯୋଡ଼ୁଛି..."


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
    asyncio.create_task(init_escalations_table_fn())
    asyncio.create_task(init_sessions_table())
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

    # Record session start for analytics (Day 8)
    call_type = "outbound" if is_outbound else "inbound"
    asyncio.create_task(start_session(
        session_id=ctx.room.name,
        user_id=user_id,
        call_type=call_type,
        language="od-IN",
    ))

    # End session when the room disconnects
    @ctx.room.on("disconnected")
    def _on_room_disconnected(*_args):
        asyncio.create_task(end_session(ctx.room.name))

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
        # openrouter/free routes to random models that don't support Odia script
        # google.LLM with gemini-2.0-flash is the only reliable multilingual option
        llm=google.LLM(
            model="gemini-3.5-flash-lite",  # Lite model has much higher rate limits than standard flash
            api_key=os.environ.get("GOOGLE_API_KEY", ""),
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
        agent=Assistant(user_id=user_id, instructions=agent_instructions, room_name=ctx.room.name),
        room=ctx.room,
    )

    # Speak the greeting and await it so the agent finishes before listening.
    # allow_interruptions=True lets the student cut in naturally mid-sentence.
    await session.say(greeting, allow_interruptions=True)


if __name__ == "__main__":
    cli.run_app(server)
