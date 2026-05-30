"""Document service — upload, processing pipeline, and management."""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.document import Document, DocumentStatus
from app.rag.ingestion import DocumentLoader
from app.rag.chunking import TextChunker
from app.rag.embeddings import EmbeddingService
from app.rag.vectorstore import QdrantVectorStore

logger = logging.getLogger(__name__)
settings = get_settings()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def _get_file_extension(filename: str) -> str:
    """Extract file extension (lowercase, no dot)."""
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


async def upload_document(
    db: AsyncSession,
    user_id: uuid.UUID,
    filename: str,
    file_content: bytes,
) -> Document:
    """
    Save an uploaded file and create a Document record.

    Raises ValueError if file type is not allowed or file is too large.
    """
    ext = _get_file_extension(filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"File type '.{ext}' is not supported. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

    if len(file_content) > MAX_FILE_SIZE:
        raise ValueError(f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)} MB")

    doc_id = uuid.uuid4()
    collection_name = f"user_{user_id}"

    # Save file to disk
    user_dir = UPLOAD_DIR / str(user_id)
    user_dir.mkdir(exist_ok=True)
    file_path = user_dir / f"{doc_id}.{ext}"
    file_path.write_bytes(file_content)

    # Create database record
    doc = Document(
        id=doc_id,
        user_id=user_id,
        filename=filename,
        file_type=ext,
        file_size=len(file_content),
        status=DocumentStatus.PROCESSING,
        collection_name=collection_name,
    )
    db.add(doc)
    await db.flush()

    return doc


async def process_document(
    db: AsyncSession,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Document:
    """
    Full document processing pipeline:
    1. Load document text
    2. Chunk into segments
    3. Generate embeddings
    4. Store in vector database

    Updates document status throughout the process.
    """
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise ValueError(f"Document {document_id} not found")

    try:
        file_path = UPLOAD_DIR / str(user_id) / f"{doc.id}.{doc.file_type}"

        # 1. Load document
        loader = DocumentLoader()
        if doc.file_type == "pdf":
            pages = loader.load_pdf(str(file_path))
        elif doc.file_type == "docx":
            pages = loader.load_docx(str(file_path))
        elif doc.file_type == "txt":
            pages = loader.load_txt(str(file_path))
        else:
            raise ValueError(f"Unsupported file type: {doc.file_type}")

        if not pages:
            raise ValueError("No text content extracted from document")

        full_text = "\n\n".join([p["text"] for p in pages])

        # Detect language
        try:
            from app.nlp.language import detect_language
            lang_result = detect_language(full_text[:2000])
            doc.language = lang_result.language
        except Exception:
            doc.language = "en"

        # 2. Chunk text
        chunker = TextChunker(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )
        metadata = {
            "source": doc.filename,
            "document_id": str(doc.id),
            "file_type": doc.file_type,
        }
        chunks = chunker.chunk_documents(pages, metadata)

        if not chunks:
            raise ValueError("No chunks generated from document")

        # 3. Generate embeddings
        embedding_service = EmbeddingService()
        chunk_texts = [c["text"] for c in chunks]
        embeddings = await embedding_service.embed_batch(chunk_texts)

        # 4. Store in vector database
        vector_store = QdrantVectorStore()
        await vector_store.ensure_collection(doc.collection_name)

        points = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            point_id = str(uuid.uuid4())
            points.append({
                "id": point_id,
                "vector": embedding,
                "payload": {
                    "text": chunk["text"],
                    "source": doc.filename,
                    "document_id": str(doc.id),
                    "page": chunk.get("metadata", {}).get("page_number", 0),
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                },
            })

        await vector_store.upsert_points(doc.collection_name, points)

        # Update document status
        doc.chunk_count = len(chunks)
        doc.status = DocumentStatus.INDEXED
        await db.flush()

        logger.info(
            f"Document {doc.filename} processed: {len(chunks)} chunks, "
            f"{len(embeddings)} embeddings, language={doc.language}"
        )

        return doc

    except Exception as e:
        logger.error(f"Document processing failed for {document_id}: {e}")
        doc.status = DocumentStatus.FAILED
        await db.flush()
        raise


async def get_documents(
    db: AsyncSession,
    user_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
) -> list[Document]:
    """List documents for a user."""
    result = await db.execute(
        select(Document)
        .where(Document.user_id == user_id)
        .order_by(desc(Document.created_at))
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_document(
    db: AsyncSession,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Document | None:
    """Get a single document by ID."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def delete_document(
    db: AsyncSession,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """Delete a document, its vectors, and its file."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id,
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        return False

    # Delete vectors from Qdrant
    try:
        vector_store = QdrantVectorStore()
        await vector_store.delete_by_document_id(
            doc.collection_name, str(doc.id)
        )
    except Exception as e:
        logger.warning(f"Failed to delete vectors for document {document_id}: {e}")

    # Delete file from disk
    try:
        file_path = UPLOAD_DIR / str(user_id) / f"{doc.id}.{doc.file_type}"
        if file_path.exists():
            file_path.unlink()
    except Exception as e:
        logger.warning(f"Failed to delete file for document {document_id}: {e}")

    await db.delete(doc)
    await db.flush()
    return True
