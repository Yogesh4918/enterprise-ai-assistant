"""Research agent — decomposes complex queries and synthesizes answers."""

from __future__ import annotations

import logging
from typing import List

import openai

from app.config import get_settings
from app.rag.chain import RAGChain, RAGResponse
from app.rag.retrieval import HybridRetriever
from app.rag.vectorstore import SearchResult

logger = logging.getLogger(__name__)


class ResearchAgent:
    """Handles complex questions by decomposing them, retrieving iteratively,
    and synthesizing a comprehensive answer."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.LLM_MODEL
        self._retriever = HybridRetriever()
        self._chain = RAGChain()

    async def research(
        self,
        query: str,
        collection: str,
        chat_history: str = "",
    ) -> RAGResponse:
        """Conduct multi-step research for a complex query.

        Steps:
        1. Decompose the query into sub-questions.
        2. Retrieve documents for each sub-question.
        3. Synthesize findings into a coherent answer.

        Parameters
        ----------
        query : str
            The user's complex question.
        collection : str
            Qdrant collection to search.
        chat_history : str
            Formatted conversation history.

        Returns
        -------
        RAGResponse
            Synthesized answer with citations.
        """
        # Step 1: Decompose the query
        sub_questions = await self._decompose_query(query)
        logger.info(
            "Decomposed query into %d sub-questions: %s",
            len(sub_questions),
            sub_questions,
        )

        # Step 2: Retrieve for each sub-question
        all_results: list[SearchResult] = []
        seen_ids: set[str] = set()

        for sq in sub_questions:
            results = await self._retriever.retrieve(
                query=sq,
                collection=collection,
                top_k=5,
                chat_history=chat_history,
            )
            for r in results:
                if r.point_id not in seen_ids:
                    seen_ids.add(r.point_id)
                    all_results.append(r)

        # Also retrieve for the original query
        original_results = await self._retriever.retrieve(
            query=query,
            collection=collection,
            top_k=5,
            chat_history=chat_history,
        )
        for r in original_results:
            if r.point_id not in seen_ids:
                seen_ids.add(r.point_id)
                all_results.append(r)

        # Sort by score and limit
        all_results.sort(key=lambda r: r.score, reverse=True)
        top_results = all_results[:15]

        # Step 3: Generate synthesized answer
        response = await self._chain.generate(
            query=query,
            context_docs=top_results,
            chat_history=chat_history,
        )

        return response

    async def _decompose_query(self, query: str) -> list[str]:
        """Break a complex question into smaller sub-questions."""
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You decompose complex questions into 2-4 simpler sub-questions "
                            "that, when answered together, fully address the original question. "
                            "Return each sub-question on its own line. "
                            "If the question is already simple, return it as-is on one line."
                        ),
                    },
                    {"role": "user", "content": query},
                ],
                temperature=0.3,
                max_tokens=512,
            )
            raw = response.choices[0].message.content or query
            sub_questions = [
                line.strip().lstrip("0123456789.-) ")
                for line in raw.strip().split("\n")
                if line.strip() and len(line.strip()) > 5
            ]
            return sub_questions if sub_questions else [query]
        except Exception as exc:
            logger.warning("Query decomposition failed: %s", exc)
            return [query]
