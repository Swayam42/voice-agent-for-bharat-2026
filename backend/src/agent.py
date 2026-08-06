import logging

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    inference,
    tokenize,
    room_io,
)
from livekit.plugins import murf, silero, google, deepgram, noise_cancellation, openai
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from sarvam_stt import SarvamSTT
import os

logger = logging.getLogger("agent")

load_dotenv()

SYSTEM_PROMPT = """You are an educational AI learning companion for students in Odisha. 
When you introduce yourself, introduce yourself as their "Saathi" (companion/friend), do not say "I am Mo Saathi".
Your primary goal is to help students learn about ANY topic they want to understand in Odia. Explain complex concepts simply, encourage curiosity, and be extremely student-friendly.
CRITICAL RULES:
1. You MUST respond entirely in pure, native Odia script (e.g., ନମସ୍କାର). This is required for the text-to-speech engine to pronounce Odia perfectly.
2. The user will often speak in English, Hindi, or Odia. Understand their context seamlessly.
3. Embrace Odia culture! If the user says "Jay Jagannath" (ଜୟ ଜଗନ୍ନାଥ), "Namaskar", or uses local terms, acknowledge it warmly and reply culturally.
4. Switch to pure English if the user explicitly asks for an English explanation.
5. DO NOT use Markdown formatting like asterisks (**) or hashes (#). 
6. Keep your answers brief, conversational, and highly educational."""


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)

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


if __name__ == "__main__":
    cli.run_app(server)
