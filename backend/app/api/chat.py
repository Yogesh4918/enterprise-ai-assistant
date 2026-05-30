"""Chat API routes — conversation CRUD and message sending."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.auth import _get_current_user
from app.schemas.chat import (
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
    ChatRequest,
)
from app.services import chat_service

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(_get_current_user),
):
    """Create a new conversation."""
    conv = await chat_service.create_conversation(
        db, user_id=current_user.id, title=payload.title
    )
    return conv


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(_get_current_user),
):
    """List all conversations for the current user."""
    return await chat_service.get_conversations(db, current_user.id, skip, limit)


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(_get_current_user),
):
    """Get a conversation with all its messages."""
    conv = await chat_service.get_conversation_with_messages(
        db, conversation_id, current_user.id
    )
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {
        "id": str(conv.id),
        "title": conv.title,
        "created_at": conv.created_at.isoformat(),
        "updated_at": conv.updated_at.isoformat(),
        "messages": [
            {
                "id": str(msg.id),
                "role": msg.role.value,
                "content": msg.content,
                "citations": msg.citations,
                "confidence_score": msg.confidence_score,
                "language": msg.language,
                "created_at": msg.created_at.isoformat(),
            }
            for msg in sorted(conv.messages, key=lambda m: m.created_at)
        ],
    }


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(_get_current_user),
):
    """Delete a conversation and all its messages."""
    deleted = await chat_service.delete_conversation(db, conversation_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: uuid.UUID,
    payload: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(_get_current_user),
):
    """Update a conversation's title."""
    conv = await chat_service.update_conversation_title(
        db, conversation_id, current_user.id, payload.title
    )
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.post("/{conversation_id}/message")
async def send_message(
    conversation_id: uuid.UUID,
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(_get_current_user),
):
    """Send a message and get a RAG-powered response (non-streaming)."""
    # Verify conversation belongs to user
    conv = await chat_service.get_conversation_with_messages(
        db, conversation_id, current_user.id
    )
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    try:
        result = await chat_service.process_message(
            db,
            conversation_id=conversation_id,
            user_id=current_user.id,
            content=payload.content,
        )
        return {
            "answer": result["answer"],
            "citations": result.get("citations", []),
            "confidence_score": result.get("confidence_score"),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}",
        )
