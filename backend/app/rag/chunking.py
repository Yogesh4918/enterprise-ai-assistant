"""Text chunking using LangChain text splitters."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, List

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """A chunk of text with associated metadata."""
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    chunk_index: int = 0
    total_chunks: int = 0


class TextChunker:
    """Splits long documents into overlapping chunks for embedding."""

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> None:
        settings = get_settings()
        self._chunk_size = chunk_size or settings.CHUNK_SIZE
        self._chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self._chunk_size,
            chunk_overlap=self._chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ", ""],
            keep_separator=True,
            is_separator_regex=False,
        )

    def chunk_text(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> List[Chunk]:
        """Split a text into overlapping chunks.

        Parameters
        ----------
        text : str
            The full text to split.
        metadata : dict
            Base metadata copied into every chunk (source, page, etc.).

        Returns
        -------
        list[Chunk]
            Ordered list of chunks with enriched metadata.
        """
        if not text or not text.strip():
            return []

        base_meta = metadata or {}
        raw_chunks = self._splitter.split_text(text)
        total = len(raw_chunks)

        chunks: List[Chunk] = []
        for idx, chunk_text in enumerate(raw_chunks):
            chunk_meta = {
                **base_meta,
                "chunk_index": idx,
                "total_chunks": total,
                "chunk_size": len(chunk_text),
            }
            chunks.append(
                Chunk(
                    text=chunk_text,
                    metadata=chunk_meta,
                    chunk_index=idx,
                    total_chunks=total,
                )
            )

        logger.debug(
            "Split text (%d chars) into %d chunks (size=%d, overlap=%d)",
            len(text),
            total,
            self._chunk_size,
            self._chunk_overlap,
        )
        return chunks

    def chunk_documents(
        self,
        documents: list[Any],
    ) -> List[Chunk]:
        """Chunk multiple LoadedDocument objects.

        Parameters
        ----------
        documents : list[LoadedDocument]
            Documents returned by DocumentLoader.

        Returns
        -------
        list[Chunk]
            All chunks across all documents, with metadata preserved.
        """
        all_chunks: List[Chunk] = []
        for doc in documents:
            doc_chunks = self.chunk_text(doc.text, metadata=doc.metadata)
            all_chunks.extend(doc_chunks)

        logger.info("Produced %d total chunks from %d documents", len(all_chunks), len(documents))
        return all_chunks
