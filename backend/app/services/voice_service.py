"""
Voice Service — sourced from voice_agents/codex.py.
STT via Google Speech Recognition, TTS via OpenAI (optional).
Gracefully degrades if dependencies are missing.
"""
import io
import logging

logger = logging.getLogger(__name__)


class VoiceService:
    def __init__(self):
        self._stt_ok = False
        self._tts_ok = False
        self._sr = None
        self._tts_client = None
        self._setup()

    def _setup(self):
        # STT
        try:
            import speech_recognition as sr
            self._sr = sr
            self._stt_ok = True
            logger.info("STT ready (Google Speech Recognition).")
        except ImportError:
            logger.warning("speech_recognition not installed — STT disabled.")

        # TTS
        try:
            from app.config import get_settings
            settings = get_settings()
            if settings.openai_api_key:
                from openai import OpenAI
                self._tts_client = OpenAI(api_key=settings.openai_api_key)
                self._tts_ok = True
                logger.info("TTS ready (OpenAI).")
            else:
                logger.warning("OPENAI_API_KEY not set — TTS disabled.")
        except Exception as e:
            logger.warning("TTS setup failed: %s", e)

    # ── STT ───────────────────────────────────────────────────────────────────
    def speech_to_text(self, audio_bytes: bytes) -> str:
        if not self._stt_ok:
            raise RuntimeError("STT not available. Install speech_recognition.")
        
        sr = self._sr
        recognizer = sr.Recognizer()
        
        try:
            from pydub import AudioSegment
            # Load audio (any format supported by ffmpeg) and export as WAV
            audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
            wav_io = io.BytesIO()
            audio_segment.export(wav_io, format="wav")
            wav_io.seek(0)
            
            with sr.AudioFile(wav_io) as source:
                audio_data = recognizer.record(source)
            return recognizer.recognize_google(audio_data)
        except ImportError:
            # Fallback if pydub/ffmpeg missing
            try:
                with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
                    audio_data = recognizer.record(source)
                return recognizer.recognize_google(audio_data)
            except sr.UnknownValueError:
                raise ValueError("Could not understand audio. Please speak clearly.")
        except Exception as e:
            logger.error("STT Conversion error: %s", e)
            # Try original bytes as fallback
            try:
                with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
                    audio_data = recognizer.record(source)
                return recognizer.recognize_google(audio_data)
            except Exception:
                raise ValueError(f"Transcription failed. Ensure audio is clear and format is supported. ({e})")

    # ── TTS ───────────────────────────────────────────────────────────────────
    def text_to_speech(self, text: str, voice: str = "nova") -> bytes:
        if not self._tts_ok:
            raise RuntimeError("TTS not available. Set OPENAI_API_KEY in .env")
        response = self._tts_client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text,
            response_format="mp3",
        )
        return response.content

    @property
    def capabilities(self) -> dict:
        return {"stt": self._stt_ok, "tts": self._tts_ok}


# Singleton
voice_service = VoiceService()
