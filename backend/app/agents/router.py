"""Intent router agent — classifies user messages into task categories."""

from __future__ import annotations

import logging
from enum import Enum

import openai

from app.config import get_settings
from app.rag.prompts import ROUTER_PROMPT

logger = logging.getLogger(__name__)


class Intent(str, Enum):
    """Possible user intents."""
    QUESTION = "question"
    SUMMARIZE = "summarize"
    TRANSLATE = "translate"
    CHAT = "chat"


class IntentRouter:
    """Uses an LLM to classify user messages into one of four intents."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.LLM_MODEL

    async def classify(self, message: str) -> Intent:
        """Classify a user message into an intent.

        Parameters
        ----------
        message : str
            The user's raw message text.

        Returns
        -------
        Intent
            The classified intent.
        """
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "user",
                        "content": ROUTER_PROMPT.format(message=message),
                    }
                ],
                temperature=0.0,
                max_tokens=10,
            )
            raw = (response.choices[0].message.content or "").strip().lower()

            # Map to enum with fuzzy matching
            intent_map = {
                "question": Intent.QUESTION,
                "summarize": Intent.SUMMARIZE,
                "summary": Intent.SUMMARIZE,
                "translate": Intent.TRANSLATE,
                "translation": Intent.TRANSLATE,
                "chat": Intent.CHAT,
                "greeting": Intent.CHAT,
                "small_talk": Intent.CHAT,
            }

            for key, intent in intent_map.items():
                if key in raw:
                    logger.info("Classified intent: %s (raw: '%s')", intent.value, raw)
                    return intent

            # Default to question for ambiguous cases
            logger.info("Ambiguous intent '%s', defaulting to QUESTION", raw)
            return Intent.QUESTION

        except Exception as exc:
            logger.error("Intent classification failed: %s", exc)
            return Intent.QUESTION
