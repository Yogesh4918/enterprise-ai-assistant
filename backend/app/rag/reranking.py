"""Cross-encoder / LLM-based reranking of search results."""

from __future__ import annotations

import logging
from typing import List

import openai

from app.config import get_settings
from app.rag.vectorstore import SearchResult

logger = logging.getLogger(__name__)


class Reranker:
    """Reranks retrieved documents using LLM-based relevance scoring.

    Uses GPT-4o to judge the relevance of each document to the query,
    producing a refined ranking that improves precision.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.LLM_MODEL

    async def rerank(
        self,
        query: str,
        documents: List[SearchResult],
        top_k: int = 10,
    ) -> List[SearchResult]:
        """Rerank documents by LLM-assessed relevance.

        For small result sets (≤5), skips the LLM call and returns as-is.
        For larger sets, scores each document and re-sorts.

        Parameters
        ----------
        query : str
            The user's original query.
        documents : list[SearchResult]
            Documents to rerank.
        top_k : int
            Number of results to return after reranking.

        Returns
        -------
        list[SearchResult]
            Sorted by descending relevance.
        """
        if not documents:
            return []

        # For small sets, skip expensive LLM reranking
        if len(documents) <= 5:
            return documents[:top_k]

        try:
            scored = await self._batch_score(query, documents)
            scored.sort(key=lambda pair: pair[0], reverse=True)
            return [doc for _, doc in scored[:top_k]]
        except Exception as exc:
            logger.warning("Reranking failed, returning original order: %s", exc)
            return documents[:top_k]

    async def _batch_score(
        self,
        query: str,
        documents: List[SearchResult],
    ) -> list[tuple[float, SearchResult]]:
        """Score all documents in a single LLM call for efficiency."""
        doc_descriptions = []
        for idx, doc in enumerate(documents):
            snippet = doc.text[:300].replace("\n", " ")
            doc_descriptions.append(f"[{idx}] {snippet}")

        docs_text = "\n".join(doc_descriptions)

        prompt = (
            "You are a relevance judge. Given a query and a list of document snippets, "
            "rate each document's relevance to the query on a scale of 0 to 10.\n\n"
            f"Query: {query}\n\n"
            f"Documents:\n{docs_text}\n\n"
            "Return your scores as a comma-separated list of numbers in order "
            "(e.g., '7,3,9,2,...'). Return ONLY the numbers, nothing else."
        )

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=256,
        )

        raw = response.choices[0].message.content or ""
        scores = self._parse_scores(raw, len(documents))

        return list(zip(scores, documents))

    @staticmethod
    def _parse_scores(raw: str, expected_count: int) -> list[float]:
        """Parse comma-separated scores, handling malformed output gracefully."""
        scores: list[float] = []
        for token in raw.replace("\n", ",").split(","):
            token = token.strip()
            if not token:
                continue
            try:
                val = float(token)
                scores.append(min(max(val, 0.0), 10.0))
            except ValueError:
                # Try to extract a number from the token
                import re

                match = re.search(r"(\d+\.?\d*)", token)
                if match:
                    scores.append(min(max(float(match.group(1)), 0.0), 10.0))

        # Pad or truncate to expected length
        if len(scores) < expected_count:
            avg = sum(scores) / len(scores) if scores else 5.0
            scores.extend([avg] * (expected_count - len(scores)))
        return scores[:expected_count]
