"""RAG chain: generates answers from context with citation extraction and streaming."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, List, Optional

import openai

from app.config import get_settings
from app.rag.prompts import CONFIDENCE_PROMPT, RAG_SYSTEM_PROMPT
from app.rag.vectorstore import SearchResult

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    """A source citation extracted from the generated answer."""
    index: int
    source: str
    text_snippet: str
    score: float = 0.0


@dataclass
class RAGResponse:
    """Full response from the RAG chain."""
    answer: str
    citations: list[Citation] = field(default_factory=list)
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class RAGChain:
    """Generates answers grounded in retrieved context documents."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.LLM_MODEL

    def _build_context(self, context_docs: List[SearchResult]) -> str:
        """Format retrieved documents into a numbered context block."""
        if not context_docs:
            return "No relevant documents found."

        parts: list[str] = []
        for idx, doc in enumerate(context_docs, start=1):
            source = doc.metadata.get("source", "Unknown")
            page = doc.metadata.get("page_number", "")
            source_info = f"Source: {source}"
            if page:
                source_info += f" (page {page})"
            parts.append(f"[{idx}] {source_info}\n{doc.text}")

        return "\n\n".join(parts)

    def _build_messages(
        self,
        query: str,
        context: str,
        chat_history: str,
    ) -> list[dict[str, str]]:
        """Construct the OpenAI message array."""
        system_content = RAG_SYSTEM_PROMPT.format(
            context=context,
            chat_history=chat_history or "No previous conversation.",
        )
        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": query},
        ]

    async def generate(
        self,
        query: str,
        context_docs: List[SearchResult],
        chat_history: str = "",
    ) -> RAGResponse:
        """Generate a complete answer with citations and confidence.

        Parameters
        ----------
        query : str
            The user's question.
        context_docs : list[SearchResult]
            Retrieved documents with scores.
        chat_history : str
            Formatted conversation history.

        Returns
        -------
        RAGResponse
            The answer, citations, and confidence score.
        """
        context = self._build_context(context_docs)
        messages = self._build_messages(query, context, chat_history)

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=0.2,
                max_tokens=2048,
            )
            answer = response.choices[0].message.content or ""
        except Exception as exc:
            logger.error("LLM generation failed: %s", exc)
            return RAGResponse(
                answer="I'm sorry, I encountered an error generating a response. Please try again.",
                confidence=0.0,
            )

        # Extract citations
        citations = self._extract_citations(answer, context_docs)

        # Calculate confidence
        confidence = await self._calculate_confidence(answer, context)

        # Build metadata
        usage = response.usage
        metadata: dict[str, Any] = {}
        if usage:
            metadata["prompt_tokens"] = usage.prompt_tokens
            metadata["completion_tokens"] = usage.completion_tokens
            metadata["total_tokens"] = usage.total_tokens

        return RAGResponse(
            answer=answer,
            citations=citations,
            confidence=confidence,
            metadata=metadata,
        )

    async def stream_generate(
        self,
        query: str,
        context_docs: List[SearchResult],
        chat_history: str = "",
    ) -> AsyncGenerator[str, None]:
        """Stream tokens of the generated answer.

        Yields
        ------
        str
            Individual tokens or small chunks of the answer.
        """
        context = self._build_context(context_docs)
        messages = self._build_messages(query, context, chat_history)

        try:
            stream = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=0.2,
                max_tokens=2048,
                stream=True,
            )

            async for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield delta.content

        except Exception as exc:
            logger.error("Streaming generation failed: %s", exc)
            yield f"\n\n[Error: {exc}]"

    def _extract_citations(
        self,
        answer: str,
        context_docs: List[SearchResult],
    ) -> list[Citation]:
        """Find [N] references in the answer and map them to source documents."""
        # Find all citation markers like [1], [2], etc.
        citation_pattern = re.compile(r"\[(\d+)\]")
        found_indices = set(int(m) for m in citation_pattern.findall(answer))

        citations: list[Citation] = []
        for idx in sorted(found_indices):
            if 1 <= idx <= len(context_docs):
                doc = context_docs[idx - 1]
                citations.append(
                    Citation(
                        index=idx,
                        source=doc.metadata.get("source", "Unknown"),
                        text_snippet=doc.text[:200],
                        score=doc.score,
                    )
                )

        return citations

    async def _calculate_confidence(
        self,
        answer: str,
        context: str,
    ) -> float:
        """Use the LLM to assess confidence in the generated answer."""
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "user",
                        "content": CONFIDENCE_PROMPT.format(
                            answer=answer[:500],
                            context=context[:1000],
                        ),
                    }
                ],
                temperature=0.0,
                max_tokens=10,
            )
            raw = response.choices[0].message.content or "0.5"
            # Extract the first float
            match = re.search(r"(\d+\.?\d*)", raw)
            if match:
                score = float(match.group(1))
                return min(max(score, 0.0), 1.0)
            return 0.5
        except Exception as exc:
            logger.warning("Confidence calculation failed: %s", exc)
            # Fallback: base confidence on retrieval scores
            return 0.5
