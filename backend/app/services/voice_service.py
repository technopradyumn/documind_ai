"""
Voice Service — STT (audio → text) and TTS (text → audio).
STT via Google Speech Recognition (requires internet).
TTS via OpenAI (optional — set OPENAI_API_KEY).
Gracefully degrades if optional dependencies are missing.
"""
import io
import logging
import tempfile
import os

logger = logging.getLogger(__name__)


class VoiceService:
    def __init__(self):
        self._stt_ok = False
        self._tts_ok = False
        self._sr = None
        self._tts_client = None
        self._pydub_ok = False
        self._setup()

    def _setup(self):
        # STT — SpeechRecognition
        try:
            import speech_recognition as sr
            self._sr = sr
            self._stt_ok = True
            logger.info("STT ready (Google Speech Recognition).")
        except ImportError:
            logger.warning("speech_recognition not installed — STT disabled. Run: pip install SpeechRecognition")

        # Pydub — for audio format conversion (webm → wav)
        try:
            from pydub import AudioSegment  # noqa: F401
            self._pydub_ok = True
            logger.info("pydub ready — audio format conversion enabled.")
        except ImportError:
            logger.warning("pydub not installed — only WAV audio supported for STT. Run: pip install pydub")

        # TTS — OpenAI (optional)
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
    def speech_to_text(self, audio_bytes: bytes, mime_type: str = "audio/webm") -> str:
        """
        Convert raw audio bytes to a transcript string.
        Accepts webm (from browser MediaRecorder), wav, mp3, ogg, etc.
        """
        if not self._stt_ok:
            raise RuntimeError(
                "STT not available on this server. "
                "Install: pip install SpeechRecognition"
            )

        sr = self._sr
        recognizer = sr.Recognizer()

        # ── Step 1: Convert to WAV using pydub (handles webm, mp3, ogg, etc.) ──
        wav_bytes = None
        if self._pydub_ok:
            try:
                from pydub import AudioSegment
                # Detect format from mime_type or try auto-detect
                fmt = "webm"
                if "mp3" in mime_type:
                    fmt = "mp3"
                elif "ogg" in mime_type:
                    fmt = "ogg"
                elif "wav" in mime_type:
                    fmt = "wav"
                elif "mp4" in mime_type or "m4a" in mime_type:
                    fmt = "mp4"

                # Use a temp file for formats pydub can't read from BytesIO
                with tempfile.NamedTemporaryFile(suffix=f".{fmt}", delete=False) as tmp:
                    tmp.write(audio_bytes)
                    tmp_path = tmp.name

                try:
                    segment = AudioSegment.from_file(tmp_path, format=fmt)
                except Exception:
                    # Try auto-detect if explicit format fails
                    segment = AudioSegment.from_file(tmp_path)
                finally:
                    os.unlink(tmp_path)

                buf = io.BytesIO()
                segment.export(buf, format="wav")
                buf.seek(0)
                wav_bytes = buf.read()
                logger.debug("Audio converted to WAV via pydub (%d bytes).", len(wav_bytes))
            except Exception as e:
                logger.warning("pydub conversion failed (%s). Trying raw bytes as WAV.", e)
                wav_bytes = None

        # ── Step 2: Transcribe with SpeechRecognition ──────────────────────────
        audio_source = io.BytesIO(wav_bytes if wav_bytes else audio_bytes)
        try:
            with sr.AudioFile(audio_source) as source:
                # Adjust for ambient noise
                recognizer.adjust_for_ambient_noise(source, duration=0.2)
                audio_data = recognizer.record(source)

            transcript = recognizer.recognize_google(audio_data)
            if not transcript:
                raise ValueError("Transcription returned empty string.")
            logger.info("STT transcript: %s", transcript[:80])
            return transcript

        except sr.UnknownValueError:
            raise ValueError(
                "Could not understand audio. Please speak clearly and ensure "
                "your microphone is working. Try again in a quieter environment."
            )
        except sr.RequestError as e:
            raise RuntimeError(
                f"Google Speech Recognition service error: {e}. "
                "Please check your internet connection."
            )
        except Exception as e:
            logger.error("STT error: %s", e, exc_info=True)
            raise ValueError(f"Transcription failed: {e}")

    # ── TTS ───────────────────────────────────────────────────────────────────
    def text_to_speech(self, text: str, voice: str = "nova") -> bytes:
        """Convert text to MP3 audio bytes using OpenAI TTS."""
        if not self._tts_ok:
            raise RuntimeError(
                "TTS not available. Set OPENAI_API_KEY in .env and restart."
            )
        try:
            response = self._tts_client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text,
                response_format="mp3",
            )
            return response.content
        except Exception as e:
            logger.error("TTS error: %s", e)
            raise RuntimeError(f"TTS failed: {e}")

    @property
    def capabilities(self) -> dict:
        return {
            "stt": self._stt_ok,
            "tts": self._tts_ok,
            "audio_conversion": self._pydub_ok,
        }


# Singleton
voice_service = VoiceService()
