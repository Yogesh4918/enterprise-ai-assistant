"""Voice API routes — transcription and speech synthesis."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response

from app.api.auth import _get_current_user
from app.services import voice_service

router = APIRouter(prefix="/api/voice", tags=["Voice"])


@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    _current_user=Depends(_get_current_user),
):
    """Transcribe audio to text using Whisper."""
    content = await audio.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty audio file")

    try:
        result = await voice_service.transcribe_audio(
            audio_data=content,
            filename=audio.filename or "audio.webm",
        )
        return {
            "text": result.text,
            "language": result.language,
            "confidence": result.confidence,
            "duration": result.duration,
        }
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@router.post("/synthesize")
async def synthesize_speech(
    text: str,
    language: str = "en",
    voice_id: str | None = None,
    _current_user=Depends(_get_current_user),
):
    """Convert text to speech audio (MP3)."""
    if not text.strip():
        raise HTTPException(status_code=400, detail="Empty text")

    try:
        audio_bytes = await voice_service.synthesize_speech(
            text=text,
            language=language,
            voice_id=voice_id,
        )
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "attachment; filename=speech.mp3"},
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Speech synthesis failed: {str(e)}")
