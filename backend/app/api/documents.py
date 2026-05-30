"""Document API routes — upload, list, status, delete."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.auth import _get_current_user
from app.schemas.document import DocumentUploadResponse, DocumentResponse
from app.services import document_service

router = APIRouter(prefix="/api/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(_get_current_user),
):
    """Upload a document for processing (PDF, DOCX, TXT)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    content = await file.read()

    try:
        doc = await document_service.upload_document(
            db,
            user_id=current_user.id,
            filename=file.filename,
            file_content=content,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Process document in background
    background_tasks.add_task(
        _process_document_background,
        document_id=doc.id,
        user_id=current_user.id,
    )

    return doc


async def _process_document_background(document_id: uuid.UUID, user_id: uuid.UUID):
    """Background task to process an uploaded document through the RAG pipeline."""
    from app.database import async_session_factory
    async with async_session_factory() as db:
        try:
            await document_service.process_document(db, document_id, user_id)
            await db.commit()
        except Exception as e:
            await db.rollback()
            import logging
            logging.getLogger(__name__).error(f"Background document processing failed: {e}")


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(_get_current_user),
):
    """List all documents for the current user."""
    docs = await document_service.get_documents(db, current_user.id, skip, limit)
    return docs


@router.get("/{document_id}/status", response_model=DocumentResponse)
async def get_document_status(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(_get_current_user),
):
    """Check the processing status of a document."""
    doc = await document_service.get_document(db, document_id, current_user.id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(_get_current_user),
):
    """Delete a document and its associated vector data."""
    deleted = await document_service.delete_document(db, document_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
