"""Document schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DocumentStatus(BaseModel):
    """Minimal status check response."""
    id: uuid.UUID
    status: str
    chunk_count: int
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}


class DocumentResponse(BaseModel):
    """Full public representation of a document."""
    id: uuid.UUID
    user_id: uuid.UUID
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    status: str
    language: Optional[str] = None
    collection_name: str
    error_message: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentUploadResponse(BaseModel):
    """Returned immediately after upload is accepted."""
    id: uuid.UUID
    filename: str
    status: str
    message: str = "Document uploaded and queued for processing."
