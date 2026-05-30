"""Retrieval module: query rewriting, multi-query, and hybrid retrieval."""

from __future__ import annotations

import logging
from typing import List

import openai

from app.config import get_settings
from app.rag.embeddings import OpenAIEmbeddingService
from app.rag.prompts import MULTI_QUERY_PROMPT, QUERY_REWRITE_PROMPT
from app.rag.vectorstore import QdrantVectorStore, SearchResult

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Orchestrates query processing and document retrieval."""

    def __init__(self) -> None:
        settings = get_settings()
        self._embedding_service = OpenAIEmbeddingService()
        self._vectorstore = QdrantVectorStore()
        self._llm_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._llm_model = settings.LLM_MODEL
        self._top_k = settings.TOP_K_RESULTS

    async def retrieve(
        self,
        query: str,
        collection: str,
        top_k: int | None = None,
        chat_history: str = "",
    ) -> List[SearchResult]:
        """Full retrieval pipeline: rewrite → embed → hybrid search → rerank.

        Parameters
        ----------
        query : str
            The user's question.
        collection : str
            Qdrant collection to search.
        top_k : int | None
            Number of results to return (defaults to settings.TOP_K_RESULTS).
        chat_history : str
            Formatted conversation history for context-aware rewriting.

        Returns
        -------
        list[SearchResult]
            Ranked search results.
        """
        k = top_k or self._top_k

        # Step 1: Rewrite query for better retrieval
        rewritten = await self.rewrite_query(query, chat_history)
        logger.info("Rewritten query: %s", rewritten)

        # Step 2: Generate embedding
        query_embedding = await self._embedding_service.embed_text(rewritten)

        # Step 3: Hybrid search
        results = await self._vectorstore.hybrid_search(
            collection=collection,
            dense_vector=query_embedding,
            top_k=k,
        )

        # Step 4: Rerank with cross-encoder scoring
        from app.rag.reranking import Reranker

        reranker = Reranker()
        reranked = await reranker.rerank(query=query, documents=results, top_k=k)

        logger.info(
            "Retrieved %d results for query '%s' in collection '%s'",
            len(reranked),
            query[:80],
            collection,
        )
        return reranked

    async def rewrite_query(self, query: str, chat_history: str = "") -> str:
        """Use the LLM to rewrite a query for optimal retrieval.

        Parameters
        ----------
        query : str
            Original user query.
        chat_history : str
            Recent conversation history.

        Returns
        -------
        str
            Rewritten, search-optimized query.
        """
        try:
            response = await self._llm_client.chat.completions.create(
                model=self._llm_model,
                messages=[
                    {
                        "role": "user",
                        "content": QUERY_REWRITE_PROMPT.format(
                            query=query,
                            chat_history=chat_history or "No previous conversation.",
                        ),
                    }
                ],
                temperature=0.0,
                max_tokens=256,
            )
            rewritten = response.choices[0].message.content
            return rewritten.strip() if rewritten else query
        except Exception as exc:
            logger.warning("Query rewrite failed, using original: %s", exc)
            return query

    async def multi_query_retrieve(
        self,
        query: str,
        collection: str,
        top_k: int | None = None,
    ) -> List[SearchResult]:
        """Generate multiple query variants, retrieve for each, and deduplicate.

        Parameters
        ----------
        query : str
            Original user query.
        collection : str
            Qdrant collection to search.
        top_k : int | None
            Number of final results to return.

        Returns
        -------
        list[SearchResult]
            Deduplicated, merged results.
        """
        k = top_k or self._top_k

        # Generate query variants
        variants = await self._generate_query_variants(query)
        all_queries = [query] + variants
        logger.info("Multi-query: searching with %d variants", len(all_queries))

        # Retrieve for each variant
        seen_ids: set[str] = set()
        all_results: list[SearchResult] = []

        for q in all_queries:
            embedding = await self._embedding_service.embed_text(q)
            results = await self._vectorstore.search(
                collection=collection,
                query_embedding=embedding,
                top_k=k,
            )
            for r in results:
                if r.point_id not in seen_ids:
                    seen_ids.add(r.point_id)
                    all_results.append(r)

        # Sort by score descending and take top_k
        all_results.sort(key=lambda r: r.score, reverse=True)

        from app.rag.reranking import Reranker

        reranker = Reranker()
        return await reranker.rerank(query=query, documents=all_results[:k * 2], top_k=k)

    async def _generate_query_variants(self, query: str) -> list[str]:
        """Ask the LLM to produce 3 alternative queries."""
        try:
            response = await self._llm_client.chat.completions.create(
                model=self._llm_model,
                messages=[
                    {
                        "role": "user",
                        "content": MULTI_QUERY_PROMPT.format(query=query),
                    }
                ],
                temperature=0.7,
                max_tokens=512,
            )
            raw = response.choices[0].message.content or ""
            variants = [
                line.strip()
                for line in raw.strip().split("\n")
                if line.strip() and len(line.strip()) > 5
            ]
            return variants[:3]
        except Exception as exc:
            logger.warning("Multi-query generation failed: %s", exc)
            return []
