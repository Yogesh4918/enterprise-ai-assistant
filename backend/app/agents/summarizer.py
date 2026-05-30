"""Summarization agent — produces structured summaries of documents."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import openai

from app.config import get_settings
from app.rag.prompts import SUMMARIZATION_PROMPT

logger = logging.getLogger(__name__)


@dataclass
class SummaryResult:
    """Result from the summarization agent."""
    summary: str
    word_count: int
    source_length: int


class SummarizationAgent:
    """Summarizes documents or text with configurable target length."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.LLM_MODEL

    async def summarize(
        self,
        content: str,
        target_length: int = 200,
    ) -> SummaryResult:
        """Generate a structured summary of the given content.

        Parameters
        ----------
        content : str
            The text to summarize.
        target_length : int
            Approximate word count for the summary.

        Returns
        -------
        SummaryResult
            The generated summary with metadata.
        """
        if not content.strip():
            return SummaryResult(summary="No content to summarize.", word_count=0, source_length=0)

        # For very long texts, chunk and summarize progressively
        if len(content) > 15000:
            return await self._progressive_summarize(content, target_length)

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "user",
                        "content": SUMMARIZATION_PROMPT.format(
                            content=content,
                            target_length=target_length,
                        ),
                    }
                ],
                temperature=0.3,
                max_tokens=max(target_length * 3, 1024),
            )
            summary = response.choices[0].message.content or ""
            summary = summary.strip()

            return SummaryResult(
                summary=summary,
                word_count=len(summary.split()),
                source_length=len(content),
            )
        except Exception as exc:
            logger.error("Summarization failed: %s", exc)
            return SummaryResult(
                summary=f"Summarization failed: {exc}",
                word_count=0,
                source_length=len(content),
            )

    async def _progressive_summarize(
        self,
        content: str,
        target_length: int,
    ) -> SummaryResult:
        """Handle very long texts by chunking and summarizing in stages.

        Split into ~10k char segments, summarize each, then combine.
        """
        chunk_size = 10000
        chunks = [content[i : i + chunk_size] for i in range(0, len(content), chunk_size)]

        logger.info(
            "Progressive summarization: %d chunks from %d chars",
            len(chunks),
            len(content),
        )

        # Stage 1: Summarize each chunk
        chunk_summaries: list[str] = []
        for idx, chunk in enumerate(chunks):
            try:
                response = await self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {
                            "role": "user",
                            "content": SUMMARIZATION_PROMPT.format(
                                content=chunk,
                                target_length=target_length // len(chunks) + 50,
                            ),
                        }
                    ],
                    temperature=0.3,
                    max_tokens=512,
                )
                summary = (response.choices[0].message.content or "").strip()
                if summary:
                    chunk_summaries.append(summary)
            except Exception as exc:
                logger.warning("Failed to summarize chunk %d: %s", idx, exc)

        # Stage 2: Combine chunk summaries into a final summary
        combined = "\n\n".join(chunk_summaries)
        final_result = await self.summarize(combined, target_length)
        final_result.source_length = len(content)

        return final_result

    async def summarize_documents(
        self,
        documents: list[dict],
        target_length: int = 300,
    ) -> SummaryResult:
        """Summarize multiple document texts together.

        Parameters
        ----------
        documents : list[dict]
            Each dict should have 'text' and optionally 'source' keys.
        target_length : int
            Approximate word count for the combined summary.

        Returns
        -------
        SummaryResult
        """
        parts: list[str] = []
        for doc in documents:
            source = doc.get("source", "Document")
            text = doc.get("text", "")
            if text:
                parts.append(f"--- {source} ---\n{text}")

        combined = "\n\n".join(parts)
        return await self.summarize(combined, target_length)
