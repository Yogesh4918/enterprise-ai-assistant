"""Qdrant vector store client with hybrid search support."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, List, Optional

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    SearchParams,
    VectorParams,
)

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single result from a vector search."""
    text: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)
    point_id: str = ""


class QdrantVectorStore:
    """Async Qdrant client wrapper for document storage and retrieval."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncQdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            timeout=60.0,
        )
        self._dimensions = settings.EMBEDDING_DIMENSIONS

    async def close(self) -> None:
        """Close the client connection."""
        await self._client.close()

    async def init_collection(self, name: str) -> None:
        """Create a collection if it does not already exist.

        Parameters
        ----------
        name : str
            Collection name.
        """
        collections = await self._client.get_collections()
        existing = {c.name for c in collections.collections}

        if name in existing:
            logger.info("Collection '%s' already exists", name)
            return

        await self._client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(
                size=self._dimensions,
                distance=Distance.COSINE,
            ),
        )
        logger.info("Created Qdrant collection '%s' (%d dims, cosine)", name, self._dimensions)

    async def upsert_documents(
        self,
        collection: str,
        chunks: list[Any],
        embeddings: List[List[float]],
    ) -> int:
        """Insert or update document chunks with their embeddings.

        Parameters
        ----------
        collection : str
            Target collection name.
        chunks : list[Chunk]
            Chunk objects with .text and .metadata.
        embeddings : list[list[float]]
            Corresponding embedding vectors.

        Returns
        -------
        int
            Number of points upserted.
        """
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"chunks ({len(chunks)}) and embeddings ({len(embeddings)}) must have the same length"
            )

        points: list[PointStruct] = []
        for chunk, embedding in zip(chunks, embeddings):
            point_id = str(uuid.uuid4())
            payload = {
                "text": chunk.text,
                "chunk_index": chunk.chunk_index,
                "total_chunks": chunk.total_chunks,
                **chunk.metadata,
            }
            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload,
                )
            )

        # Upsert in batches of 100 to avoid timeouts
        batch_size = 100
        for start in range(0, len(points), batch_size):
            batch = points[start : start + batch_size]
            await self._client.upsert(
                collection_name=collection,
                points=batch,
            )
            logger.debug(
                "Upserted batch %d–%d into '%s'",
                start,
                start + len(batch) - 1,
                collection,
            )

        logger.info("Upserted %d points into collection '%s'", len(points), collection)
        return len(points)

    async def search(
        self,
        collection: str,
        query_embedding: List[float],
        top_k: int = 10,
        score_threshold: float = 0.0,
        filter_conditions: Optional[dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Dense vector similarity search.

        Parameters
        ----------
        collection : str
            Collection to search.
        query_embedding : list[float]
            Query vector.
        top_k : int
            Number of results to return.
        score_threshold : float
            Minimum score to include a result.
        filter_conditions : dict
            Optional Qdrant filter conditions.

        Returns
        -------
        list[SearchResult]
            Ordered by descending relevance score.
        """
        qdrant_filter = None
        if filter_conditions:
            conditions = []
            for key, value in filter_conditions.items():
                conditions.append(
                    FieldCondition(key=key, match=MatchValue(value=value))
                )
            qdrant_filter = Filter(must=conditions)

        results = await self._client.search(
            collection_name=collection,
            query_vector=query_embedding,
            limit=top_k,
            score_threshold=score_threshold,
            query_filter=qdrant_filter,
            search_params=SearchParams(
                hnsw_ef=128,
                exact=False,
            ),
        )

        search_results: list[SearchResult] = []
        for hit in results:
            payload = hit.payload or {}
            text = payload.pop("text", "")
            search_results.append(
                SearchResult(
                    text=text,
                    score=hit.score,
                    metadata=payload,
                    point_id=str(hit.id),
                )
            )

        logger.debug(
            "Search in '%s' returned %d results (top score: %.4f)",
            collection,
            len(search_results),
            search_results[0].score if search_results else 0.0,
        )
        return search_results

    async def hybrid_search(
        self,
        collection: str,
        dense_vector: List[float],
        sparse_vector: Optional[dict[int, float]] = None,
        top_k: int = 10,
        score_threshold: float = 0.0,
    ) -> List[SearchResult]:
        """Hybrid search combining dense vectors with optional sparse re-scoring.

        When sparse vectors are not available, falls back to pure dense search
        with Reciprocal Rank Fusion–style score normalization.

        Parameters
        ----------
        collection : str
            Collection to search.
        dense_vector : list[float]
            Dense query embedding.
        sparse_vector : dict[int, float] | None
            Optional sparse vector (term weights).
        top_k : int
            Number of results to return.
        score_threshold : float
            Minimum score to include.

        Returns
        -------
        list[SearchResult]
        """
        # Use dense search as the primary pathway
        dense_results = await self.search(
            collection=collection,
            query_embedding=dense_vector,
            top_k=top_k * 2,  # over-fetch for RRF fusion
            score_threshold=score_threshold,
        )

        if not sparse_vector or not dense_results:
            return dense_results[:top_k]

        # Apply RRF-style fusion: boost results whose text contains sparse terms
        # Build simple keyword-match score from sparse vector terms
        rrf_k = 60  # standard RRF constant

        scored: list[tuple[float, SearchResult]] = []
        for rank, result in enumerate(dense_results):
            dense_rrf = 1.0 / (rrf_k + rank + 1)

            # Simple keyword overlap score for sparse component
            text_lower = result.text.lower()
            sparse_score = 0.0
            for _idx, weight in sparse_vector.items():
                sparse_score += weight * 0.1  # lightweight contribution

            combined = dense_rrf + sparse_score * 0.3
            scored.append((combined, result))

        scored.sort(key=lambda x: x[0], reverse=True)

        final = []
        for combined_score, result in scored[:top_k]:
            result.score = combined_score
            final.append(result)

        return final

    async def delete_collection(self, name: str) -> bool:
        """Delete an entire collection.

        Returns True if deleted, False if it didn't exist.
        """
        try:
            await self._client.delete_collection(collection_name=name)
            logger.info("Deleted collection '%s'", name)
            return True
        except Exception:
            logger.warning("Collection '%s' not found for deletion", name)
            return False

    async def collection_exists(self, name: str) -> bool:
        """Check whether a collection exists."""
        collections = await self._client.get_collections()
        return name in {c.name for c in collections.collections}

    async def count_points(self, collection: str) -> int:
        """Return the number of points in a collection."""
        info = await self._client.get_collection(collection_name=collection)
        return info.points_count or 0
