"""Redis-backed conversation memory for the RAG pipeline."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import List, Optional

import redis.asyncio as aioredis

from app.config import get_settings

logger = logging.getLogger(__name__)

_HISTORY_PREFIX = "chat:history:"
_SUMMARY_PREFIX = "chat:summary:"
_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days


@dataclass
class MemoryMessage:
    """In-memory representation of a conversation message."""
    role: str
    content: str
    timestamp: str


class ConversationMemory:
    """Redis-backed sliding-window conversation memory with auto-summarization and in-memory fallback."""

    def __init__(self) -> None:
        settings = get_settings()
        self._redis: Optional[aioredis.Redis] = None
        self._redis_url = settings.REDIS_URL
        self._llm_model = settings.LLM_MODEL
        self._openai_key = settings.OPENAI_API_KEY
        self._in_memory_history: dict[str, list[MemoryMessage]] = {}
        self._in_memory_summaries: dict[str, str] = {}
        self._use_in_memory = False

    async def _get_redis(self) -> Optional[aioredis.Redis]:
        """Lazy-init the Redis connection, falling back to in-memory if Redis is unavailable."""
        if self._use_in_memory:
            return None

        if self._redis is None:
            try:
                self._redis = aioredis.from_url(
                    self._redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2,
                )
                await self._redis.ping()
            except Exception as exc:
                logger.warning("Redis connection failed. Falling back to in-memory storage: %s", exc)
                self._use_in_memory = True
                self._redis = None
        return self._redis

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._redis is not None:
            try:
                await self._redis.close()
            except Exception:
                pass
            self._redis = None

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
    ) -> None:
        """Append a message to the conversation history."""
        msg = MemoryMessage(
            role=role,
            content=content,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        r = await self._get_redis()
        if r is None:
            if conversation_id not in self._in_memory_history:
                self._in_memory_history[conversation_id] = []
            self._in_memory_history[conversation_id].append(msg)
            if len(self._in_memory_history[conversation_id]) > 30:
                await self.summarize_if_needed(conversation_id)
            return

        key = f"{_HISTORY_PREFIX}{conversation_id}"
        await r.rpush(key, json.dumps(asdict(msg)))
        await r.expire(key, _TTL_SECONDS)

        # Check if summarization is needed (every 30 messages)
        length = await r.llen(key)
        if length > 30:
            await self.summarize_if_needed(conversation_id)

    async def get_history(
        self,
        conversation_id: str,
        limit: int = 20,
    ) -> List[MemoryMessage]:
        """Retrieve recent conversation history."""
        r = await self._get_redis()
        if r is None:
            hist = self._in_memory_history.get(conversation_id, [])
            return hist[-limit:]

        key = f"{_HISTORY_PREFIX}{conversation_id}"
        raw_messages = await r.lrange(key, -limit, -1)
        messages: list[MemoryMessage] = []
        for raw in raw_messages:
            try:
                data = json.loads(raw)
                messages.append(MemoryMessage(**data))
            except (json.JSONDecodeError, TypeError) as exc:
                logger.warning("Skipping malformed message: %s", exc)

        return messages

    async def get_formatted_history(
        self,
        conversation_id: str,
        limit: int = 20,
    ) -> str:
        """Return history as a formatted string for prompt injection.

        Parameters
        ----------
        conversation_id : str
            Unique conversation identifier.
        limit : int
            Maximum number of messages to include.

        Returns
        -------
        str
            Formatted conversation history.
        """
        # Prepend summary if available
        summary = await self._get_summary(conversation_id)
        messages = await self.get_history(conversation_id, limit)

        parts: list[str] = []
        if summary:
            parts.append(f"[Previous conversation summary]: {summary}")

        for msg in messages:
            parts.append(f"{msg.role}: {msg.content}")

        return "\n".join(parts) if parts else "No previous conversation."

    async def summarize_if_needed(self, conversation_id: str) -> None:
        """Summarize older messages to keep context window manageable."""
        r = await self._get_redis()
        
        if r is None:
            hist = self._in_memory_history.get(conversation_id, [])
            length = len(hist)
            if length <= 20:
                return
            keep_recent = 10
            to_summarize_count = length - keep_recent
            old_messages = [f"{msg.role}: {msg.content}" for msg in hist[:to_summarize_count]]
        else:
            key = f"{_HISTORY_PREFIX}{conversation_id}"
            length = await r.llen(key)
            if length <= 20:
                return
            keep_recent = 10
            to_summarize_count = length - keep_recent
            raw_old = await r.lrange(key, 0, to_summarize_count - 1)
            old_messages = []
            for raw in raw_old:
                try:
                    data = json.loads(raw)
                    old_messages.append(f"{data['role']}: {data['content']}")
                except (json.JSONDecodeError, TypeError):
                    continue

        if not old_messages:
            return

        # Get existing summary
        existing_summary = await self._get_summary(conversation_id)

        # Generate summary via LLM
        summary_input = "\n".join(old_messages)
        if existing_summary:
            summary_input = f"Previous summary: {existing_summary}\n\nNew messages:\n{summary_input}"

        try:
            import openai

            client = openai.AsyncOpenAI(api_key=self._openai_key)
            response = await client.chat.completions.create(
                model=self._llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Summarize this conversation concisely, preserving key facts, "
                            "decisions, and context that would be needed for continued conversation. "
                            "Keep it under 200 words."
                        ),
                    },
                    {"role": "user", "content": summary_input},
                ],
                temperature=0.3,
                max_tokens=300,
            )
            summary = response.choices[0].message.content or ""
        except Exception as exc:
            logger.error("Failed to generate summary: %s", exc)
            return

        # Store summary and trim old messages
        if r is None:
            self._in_memory_summaries[conversation_id] = summary
            self._in_memory_history[conversation_id] = hist[to_summarize_count:]
        else:
            summary_key = f"{_SUMMARY_PREFIX}{conversation_id}"
            key = f"{_HISTORY_PREFIX}{conversation_id}"
            await r.set(summary_key, summary, ex=_TTL_SECONDS)
            await r.ltrim(key, to_summarize_count, -1)

        logger.info(
            "Summarized %d messages for conversation %s",
            to_summarize_count,
            conversation_id,
        )

    async def _get_summary(self, conversation_id: str) -> str:
        """Retrieve the stored conversation summary."""
        r = await self._get_redis()
        if r is None:
            return self._in_memory_summaries.get(conversation_id, "")

        summary_key = f"{_SUMMARY_PREFIX}{conversation_id}"
        return await r.get(summary_key) or ""

    async def clear(self, conversation_id: str) -> None:
        """Delete all history and summary for a conversation."""
        r = await self._get_redis()
        if r is None:
            self._in_memory_history.pop(conversation_id, None)
            self._in_memory_summaries.pop(conversation_id, None)
            logger.info("Cleared memory for conversation %s", conversation_id)
            return

        await r.delete(
            f"{_HISTORY_PREFIX}{conversation_id}",
            f"{_SUMMARY_PREFIX}{conversation_id}",
        )
        logger.info("Cleared memory for conversation %s", conversation_id)
