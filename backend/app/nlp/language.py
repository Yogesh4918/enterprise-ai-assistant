"""Language detection service using langdetect."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from langdetect import detect, detect_langs, LangDetectException

logger = logging.getLogger(__name__)


@dataclass
class LanguageResult:
    """Result of language detection."""
    language: str
    confidence: float
    all_languages: list[dict[str, float]]


def detect_language(text: str) -> LanguageResult:
    """
    Detect the language of the given text.

    Args:
        text: Input text to analyze.

    Returns:
        LanguageResult with detected language code, confidence, and all candidates.
    """
    if not text or len(text.strip()) < 3:
        return LanguageResult(language="en", confidence=0.0, all_languages=[])

    try:
        primary_lang = detect(text)
        lang_probs = detect_langs(text)

        all_langs = [
            {"language": str(lp).split(":")[0], "confidence": lp.prob}
            for lp in lang_probs
        ]

        top_confidence = lang_probs[0].prob if lang_probs else 0.0

        return LanguageResult(
            language=primary_lang,
            confidence=top_confidence,
            all_languages=all_langs,
        )

    except LangDetectException as e:
        logger.warning(f"Language detection failed: {e}")
        return LanguageResult(language="en", confidence=0.0, all_languages=[])


LANGUAGE_NAMES: dict[str, str] = {
    "en": "English", "es": "Spanish", "fr": "French", "de": "German",
    "it": "Italian", "pt": "Portuguese", "nl": "Dutch", "ru": "Russian",
    "zh-cn": "Chinese (Simplified)", "zh-tw": "Chinese (Traditional)",
    "ja": "Japanese", "ko": "Korean", "ar": "Arabic", "hi": "Hindi",
    "bn": "Bengali", "tr": "Turkish", "vi": "Vietnamese", "th": "Thai",
    "pl": "Polish", "uk": "Ukrainian", "sv": "Swedish", "da": "Danish",
    "no": "Norwegian", "fi": "Finnish", "cs": "Czech", "ro": "Romanian",
    "hu": "Hungarian", "el": "Greek", "he": "Hebrew", "id": "Indonesian",
    "ms": "Malay", "tl": "Filipino", "sw": "Swahili",
}


def get_language_name(code: str) -> str:
    """Get human-readable language name from ISO 639-1 code."""
    return LANGUAGE_NAMES.get(code, code.upper())
