"""
Voice route — STT (audio → text) and TTS (text → audio).
POST /api/voice/stt
POST /api/voice/tts
GET  /api/voice/status
"""
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response

from app.models.schemas import VoiceSTTResponse, VoiceTTSRequest
from app.services.voice_service import voice_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/voice", tags=["Voice"])


@router.get("/status")
async def voice_status():
    """Check which voice capabilities are available."""
    return voice_service.capabilities


@router.post("/stt", response_model=VoiceSTTResponse)
async def speech_to_text(audio: UploadFile = File(...)):
    """Convert uploaded audio (WAV/WebM/MP3) to transcript text."""
    if not voice_service.capabilities["stt"]:
        raise HTTPException(status_code=503, detail="STT not available on this server.")
    try:
        audio_bytes = await audio.read()
        mime_type = audio.content_type or "audio/webm"
        transcript = voice_service.speech_to_text(audio_bytes, mime_type=mime_type)
        return VoiceSTTResponse(transcript=transcript)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error("Unexpected STT error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@router.post("/tts")
async def text_to_speech(request: VoiceTTSRequest):
    """Convert text to MP3 audio bytes."""
    if not voice_service.capabilities["tts"]:
        raise HTTPException(status_code=503, detail="TTS not available. Set OPENAI_API_KEY.")
    try:
        audio_bytes = voice_service.text_to_speech(request.text, voice=request.voice)
        return Response(content=audio_bytes, media_type="audio/mpeg")
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
