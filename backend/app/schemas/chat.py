"""Chat & conversation schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    """Payload for creating a conversation."""
    title: str = Field("New Conversation", max_length=512)


class ConversationUpdate(BaseModel):
    """Payload for renaming a conversation."""
    title: str = Field(..., max_length=512)


class MessageResponse(BaseModel):
    """Public representation of a message."""
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    citations: Optional[dict[str, Any]] = None
    confidence_score: Optional[float] = None
    language: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    """Public representation of a conversation."""
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse] = []

    model_config = {"from_attributes": True}


class ConversationListItem(BaseModel):
    """Lightweight item for listing conversations (no messages)."""
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    """Payload for sending a user message."""
    content: str = Field(..., min_length=1, max_length=32_000)
    language: Optional[str] = None


class ChatRequest(BaseModel):
    """Full chat request body."""
    message: str = Field(..., min_length=1, max_length=32_000)
    conversation_id: Optional[uuid.UUID] = None
    collection_name: str = "default"
    stream: bool = False


class ChatStreamEvent(BaseModel):
    """Server-sent event payload for streaming chat."""
    type: str = Field(
        ..., description="One of: token, citation, done, error"
    )
    data: Any = None
