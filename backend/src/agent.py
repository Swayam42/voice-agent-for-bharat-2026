import logging
import os

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
    cli,
    llm,
    room_io,
    tokenize,
)
from livekit.plugins import murf, noise_cancellation, openai, silero

from sarvam_stt import SarvamSTT

logger = logging.getLogger("agent")

load_dotenv()

SYSTEM_PROMPT = """# IDENTITY
You are "Saathi", a friendly, patient, and highly encouraging educational AI learning companion for students in Odisha. You work for the students to make learning fun and accessible.
DO NOT introduce yourself or say 'Namaskar' or 'Jay Jagannath' or greet the user. The system has already greeted the user for you. Dive straight into answering their first question without any pleasantries.

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
3. For any diagnosis, medical, or harmful out-of-scope requests, you MUST explicitly decline and end with this exact escalation script: "ମୋର ସେହି ବିଷୟରେ ପରାମର୍ଶ ଦେବାର କ୍ଷମତା ନାହିଁ। ଦୟାକରି ଆପଣଙ୍କ ଶିକ୍ଷକ କିମ୍ବା ପିତାମାତାଙ୍କୁ ପଚାରନ୍ତୁ।" (I don't have the ability to advise on that. Please ask your teacher or parents.)

# VOICE OPTIMIZATION
Plain text only. No markdown. No bullet lists.
Never speak in paragraphs. Prefer 8-15 word sentences.
Pause naturally. Avoid reading like a textbook. Sound like a friendly teacher. Ask one question at a time."""


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)
        # A smaller, faster model generates the filler phrase
        self._fast_llm = openai.LLM(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY", ""),
            model="google/gemini-3.5-flash-lite",
            extra_body={"max_tokens": 10}
        )
        self._fast_llm_prompt = llm.ChatMessage(
            role="system",
            content=[
                "Generate a highly natural, instantaneous 1-to-2 word conversational acknowledgment in pure Odia script based on the user's latest input.",
                "Act like a friendly human listening. Do not answer the question directly. Keep it to 1-2 words only.",
                "Use natural human sounds like 'ଆଚ୍ଛା...' (Acha...), 'ହଁ...' (Yeah...), 'ଦେଖିବା...' (Let's see...), 'ବୁଝିଲି...' (Understood...), or 'ଠିକ୍ ଅଛି...' (Alright...).",
                "Do NOT use robotic phrases.",
            ],
        )

    async def on_user_turn_completed(
        self, turn_ctx: ChatContext, new_message: ChatMessage,
    ) -> None:
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

server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def my_agent(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }
    session = AgentSession(
        stt=SarvamSTT(language_code="od-IN"),
        llm=openai.LLM(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY", ""),
            model="google/gemini-3.5-flash-lite",
            extra_body={"max_tokens": 1000}
        ),
        tts=murf.TTS(
            voice="Anisha",
            locale="or-IN",
            model="FALCON",
            style="Conversational",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True
        ),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )
    @session.on("metrics_collected")
    def _on_metrics_collected(metrics):
        if hasattr(metrics, "end_of_utterance_delay"):
            logger.info(f"Latency (End-of-user-speech to first audio out): {metrics.end_of_utterance_delay:.2f}s")
    await session.start(
        agent=Assistant(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: (
                    noise_cancellation.BVCTelephony()
                    if params.participant.kind
                    == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                    else noise_cancellation.BVC()
                ),
            ),
        ),
    )

    await ctx.connect()
    
    # Day 2: First-turn greeting
    session.say("ନମସ୍କାର! ଜୟ ଜଗନ୍ନାଥ! ମୁଁ ତୁମର ସାଥୀ। ଆଜି କଣ ଶିଖିବାକୁ ଚାହୁଁଛ?")


if __name__ == "__main__":
    cli.run_app(server)
