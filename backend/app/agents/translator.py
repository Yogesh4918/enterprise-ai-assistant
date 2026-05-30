"""Translation agent — handles cross-language queries and responses."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import openai

from app.config import get_settings
from app.rag.prompts import TRANSLATION_PROMPT

logger = logging.getLogger(__name__)

# Common language codes to full names
LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "nl": "Dutch",
    "ru": "Russian",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "ar": "Arabic",
    "hi": "Hindi",
    "tr": "Turkish",
    "pl": "Polish",
    "sv": "Swedish",
    "da": "Danish",
    "no": "Norwegian",
    "fi": "Finnish",
    "uk": "Ukrainian",
}


@dataclass
class TranslationResult:
    """Result from the translation agent."""
    translated_text: str
    source_language: str
    target_language: str
    word_count: int


class TranslationAgent:
    """Translates text between languages using the LLM."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.LLM_MODEL

    async def translate(
        self,
        text: str,
        target_language: str = "en",
        source_language: str | None = None,
    ) -> TranslationResult:
        """Translate text to the target language.

        Parameters
        ----------
        text : str
            The text to translate.
        target_language : str
            Target language code (e.g., 'en', 'fr', 'es').
        source_language : str | None
            Source language code. If None, the LLM will auto-detect.

        Returns
        -------
        TranslationResult
            The translated text with metadata.
        """
        if not text.strip():
            return TranslationResult(
                translated_text="",
                source_language=source_language or "unknown",
                target_language=target_language,
                word_count=0,
            )

        # Detect source language if not provided
        if not source_language:
            source_language = await self._detect_language(text)

        # If source and target are the same, return as-is
        if source_language == target_language:
            return TranslationResult(
                translated_text=text,
                source_language=source_language,
                target_language=target_language,
                word_count=len(text.split()),
            )

        source_name = LANGUAGE_NAMES.get(source_language, source_language)
        target_name = LANGUAGE_NAMES.get(target_language, target_language)

        try:
            # Handle very long texts by chunking
            if len(text) > 8000:
                translated = await self._translate_long(text, source_name, target_name)
            else:
                translated = await self._translate_single(text, source_name, target_name)

            return TranslationResult(
                translated_text=translated,
                source_language=source_language,
                target_language=target_language,
                word_count=len(translated.split()),
            )
        except Exception as exc:
            logger.error("Translation failed: %s", exc)
            return TranslationResult(
                translated_text=f"Translation failed: {exc}",
                source_language=source_language,
                target_language=target_language,
                word_count=0,
            )

    async def _translate_single(
        self,
        text: str,
        source_name: str,
        target_name: str,
    ) -> str:
        """Translate a single text block."""
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "user",
                    "content": TRANSLATION_PROMPT.format(
                        text=text,
                        source_language=source_name,
                        target_language=target_name,
                    ),
                }
            ],
            temperature=0.2,
            max_tokens=4096,
        )
        return (response.choices[0].message.content or "").strip()

    async def _translate_long(
        self,
        text: str,
        source_name: str,
        target_name: str,
    ) -> str:
        """Translate a long text by splitting into chunks at paragraph boundaries."""
        paragraphs = text.split("\n\n")
        chunks: list[str] = []
        current_chunk: list[str] = []
        current_length = 0

        for para in paragraphs:
            if current_length + len(para) > 6000 and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_length = 0
            current_chunk.append(para)
            current_length += len(para)

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        translated_parts: list[str] = []
        for chunk in chunks:
            translated = await self._translate_single(chunk, source_name, target_name)
            translated_parts.append(translated)

        return "\n\n".join(translated_parts)

    async def _detect_language(self, text: str) -> str:
        """Auto-detect the language of the given text."""
        try:
            from langdetect import detect

            return detect(text[:500])
        except Exception:
            return "en"
