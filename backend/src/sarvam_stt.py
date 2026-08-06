import asyncio
import wave
import os
import tempfile
import uuid
import logging

from livekit import rtc
from livekit.agents import stt
from sarvamai import SarvamAI

logger = logging.getLogger("sarvam-stt")

class SarvamSTT(stt.STT):
    def __init__(self, api_key: str | None = None, language_code: str = "od-IN"):
        super().__init__(
            capabilities=stt.STTCapabilities(streaming=False, interim_results=False)
        )
        api_key = api_key or os.environ.get("SARVAM_API_KEY")
        if not api_key:
            raise ValueError("SARVAM_API_KEY is required in environment variables")
        self._client = SarvamAI(api_subscription_key=api_key)
        self._language_code = language_code
        logger.info(f"Sarvam STT Initialized (Language: {self._language_code})")

    async def _recognize_impl(
        self,
        buffer,
        **kwargs,
    ) -> stt.SpeechEvent:
        if not buffer:
            return stt.SpeechEvent(type=stt.SpeechEventType.FINAL_TRANSCRIPT, alternatives=[])
            
        # Buffer can be a single AudioFrame or a list of AudioFrames
        if isinstance(buffer, rtc.AudioFrame):
            frames = [buffer]
        else:
            frames = buffer
            
        if not frames:
            return stt.SpeechEvent(type=stt.SpeechEventType.FINAL_TRANSCRIPT, alternatives=[])
            
        sample_rate = frames[0].sample_rate
        num_channels = frames[0].num_channels
        
        # Resample to 16000 Hz, which is the standard for ASR models
        resampler = rtc.AudioResampler(input_rate=sample_rate, output_rate=16000, num_channels=num_channels)
        resampled_frames = []
        for f in frames:
            resampled_frames.extend(resampler.push(f))
        resampled_frames.extend(resampler.flush())
        
        raw_audio = b"".join(bytes(f.data) for f in resampled_frames)
        duration_sec = len(raw_audio) / (16000 * 2) # 16-bit PCM = 2 bytes per sample
        
        logger.info(f"Voice detected: Processing {duration_sec:.2f}s of audio...")
        
        # Save to temp file
        tmp_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.wav")
        with wave.open(tmp_path, "wb") as wav_file:
            wav_file.setnchannels(num_channels)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(16000)
            wav_file.writeframes(raw_audio)
            
        def do_transcribe():
            try:
                with open(tmp_path, "rb") as audio_file:
                    res = self._client.speech_to_text.transcribe(
                        file=audio_file,
                        language_code=self._language_code,
                        model="saaras:v3"
                    )
                if res.transcript:
                    logger.info(f"Transcribed (Sarvam): '{res.transcript}'")
                else:
                    logger.info("Transcribed (Sarvam): [No speech recognized]")
                return res.transcript
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                    
        try:
            transcript = await asyncio.to_thread(do_transcribe)
            return stt.SpeechEvent(
                type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                alternatives=[stt.SpeechData(text=transcript, language=self._language_code)] if transcript else []
            )
        except Exception as e:
            logger.error(f"Sarvam STT Error: {e}")
            return stt.SpeechEvent(type=stt.SpeechEventType.FINAL_TRANSCRIPT, alternatives=[])
