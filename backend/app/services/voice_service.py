"""Voice service — speech-to-text (Faster-Whisper) and text-to-speech (ElevenLabs/fallback)."""

from __future__ import annotations

import io
import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_whisper_model = None


@dataclass
class TranscriptionResult:
    """Result of speech-to-text transcription."""
    text: str
    language: str
    confidence: float
    duration: float


def _get_whisper_model():
    """Lazy-load Whisper model."""
    global _whisper_model
    if _whisper_model is None:
        try:
            from faster_whisper import WhisperModel
            _whisper_model = WhisperModel(
                settings.WHISPER_MODEL,
                device="cpu",
                compute_type="int8",
            )
            logger.info(f"Loaded Whisper model: {settings.WHISPER_MODEL}")
        except ImportError:
            logger.warning("faster-whisper not installed. Voice transcription unavailable.")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
    return _whisper_model


async def transcribe_audio(audio_data: bytes, filename: str = "audio.webm") -> TranscriptionResult:
    """
    Transcribe audio to text using Faster-Whisper.

    Args:
        audio_data: Raw audio bytes (WAV, MP3, WebM, etc.)
        filename: Original filename for format detection.

    Returns:
        TranscriptionResult with text, detected language, confidence, and duration.
    """
    model = _get_whisper_model()
    if model is None:
        raise RuntimeError("Whisper model is not available. Install faster-whisper.")

    # Write audio to temp file (Whisper needs a file path)
    suffix = Path(filename).suffix or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_data)
        tmp_path = tmp.name

    try:
        segments, info = model.transcribe(
            tmp_path,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=500,
                speech_pad_ms=200,
            ),
        )

        # Collect all segment texts
        texts = []
        total_confidence = 0.0
        segment_count = 0

        for segment in segments:
            texts.append(segment.text.strip())
            total_confidence += segment.avg_logprob
            segment_count += 1

        full_text = " ".join(texts).strip()
        avg_confidence = (total_confidence / segment_count) if segment_count > 0 else 0.0
        # Convert log probability to 0-1 scale (approximate)
        confidence_score = min(1.0, max(0.0, 1.0 + avg_confidence))

        return TranscriptionResult(
            text=full_text,
            language=info.language or "en",
            confidence=confidence_score,
            duration=info.duration or 0.0,
        )

    finally:
        # Clean up temp file
        try:
            Path(tmp_path).unlink()
        except OSError:
            pass


async def synthesize_speech(
    text: str,
    language: str = "en",
    voice_id: str | None = None,
) -> bytes:
    """
    Convert text to speech audio.

    Uses ElevenLabs API if API key is configured, otherwise raises an error.

    Args:
        text: Text to synthesize.
        language: Language code.
        voice_id: ElevenLabs voice ID (optional, uses default from config).

    Returns:
        Audio bytes in MP3 format.
    """
    if not settings.ELEVENLABS_API_KEY:
        raise RuntimeError(
            "Text-to-speech requires an ElevenLabs API key. "
            "Set ELEVENLABS_API_KEY in your environment."
        )

    import httpx

    target_voice = voice_id or settings.ELEVENLABS_VOICE_ID
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{target_voice}"

    headers = {
        "xi-api-key": settings.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }

    payload = {
        "text": text[:5000],  # ElevenLabs limit
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True,
        },
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.content


async def synthesize_speech_stream(
    text: str,
    voice_id: str | None = None,
):
    """
    Stream TTS audio chunks from ElevenLabs.

    Yields audio bytes as they arrive.
    """
    if not settings.ELEVENLABS_API_KEY:
        raise RuntimeError("ElevenLabs API key not configured.")

    import httpx

    target_voice = voice_id or settings.ELEVENLABS_VOICE_ID
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{target_voice}/stream"

    headers = {
        "xi-api-key": settings.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }

    payload = {
        "text": text[:5000],
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
        },
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", url, json=payload, headers=headers) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes(chunk_size=4096):
                yield chunk
