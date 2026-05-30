"""OpenAI embedding service for generating text embeddings."""

from __future__ import annotations

import asyncio
import logging
from typing import List

import openai
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

logger = logging.getLogger(__name__)


class OpenAIEmbeddingService:
    """Generates embeddings using the OpenAI text-embedding API."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.EMBEDDING_MODEL
        self._dimensions = settings.EMBEDDING_DIMENSIONS

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def embed_text(self, text: str) -> List[float]:
        """Generate an embedding for a single text string.

        Parameters
        ----------
        text : str
            The input text to embed.

        Returns
        -------
        list[float]
            A 1536-dimensional embedding vector.
        """
        text = text.replace("\n", " ").strip()
        if not text:
            return [0.0] * self._dimensions

        response = await self._client.embeddings.create(
            input=[text],
            model=self._model,
            dimensions=self._dimensions,
        )
        return response.data[0].embedding

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 100,
    ) -> List[List[float]]:
        """Generate embeddings for multiple texts, batching API calls.

        Parameters
        ----------
        texts : list[str]
            Input texts to embed.
        batch_size : int
            Maximum number of texts per API call (OpenAI supports up to ~2048).

        Returns
        -------
        list[list[float]]
            List of embedding vectors in the same order as the input texts.
        """
        if not texts:
            return []

        cleaned = [t.replace("\n", " ").strip() or "empty" for t in texts]
        all_embeddings: List[List[float]] = []

        for start in range(0, len(cleaned), batch_size):
            batch = cleaned[start : start + batch_size]
            logger.debug(
                "Embedding batch %d–%d of %d texts",
                start,
                start + len(batch) - 1,
                len(cleaned),
            )
            response = await self._client.embeddings.create(
                input=batch,
                model=self._model,
                dimensions=self._dimensions,
            )
            # Sort by index to guarantee order
            sorted_data = sorted(response.data, key=lambda d: d.index)
            all_embeddings.extend(d.embedding for d in sorted_data)

            # Respect rate limits between batches
            if start + batch_size < len(cleaned):
                await asyncio.sleep(0.1)

        return all_embeddings
