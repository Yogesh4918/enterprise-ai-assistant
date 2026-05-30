"""Analytics API route — usage stats and admin metrics."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.auth import _get_current_user
from app.services import analytics_service
from app.models.user import UserRole

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/usage")
async def get_usage_stats(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(_get_current_user),
):
    """Get usage statistics for the current user."""
    stats = await analytics_service.get_usage_stats(db, current_user.id)
    return stats


@router.get("/admin")
async def get_admin_stats(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(_get_current_user),
):
    """Get system-wide statistics (admin only)."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    stats = await analytics_service.get_admin_stats(db)
    return stats


@router.get("/conversations/activity")
async def get_conversation_activity(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(_get_current_user),
):
    """Get daily message counts for the last N days."""
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select, func, cast, Date

    from app.models.chat import Message, Conversation

    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(
            cast(Message.created_at, Date).label("date"),
            func.count(Message.id).label("count"),
        )
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Conversation.user_id == current_user.id,
            Message.created_at >= start_date,
        )
        .group_by(cast(Message.created_at, Date))
        .order_by(cast(Message.created_at, Date))
    )

    activity = [
        {"date": str(row.date), "count": row.count}
        for row in result.all()
    ]
    return {"activity": activity}


@router.get("/documents/stats")
async def get_document_stats(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(_get_current_user),
):
    """Get document statistics by file type and status."""
    from sqlalchemy import select, func

    from app.models.document import Document

    # By file type
    type_result = await db.execute(
        select(
            Document.file_type,
            func.count(Document.id).label("count"),
            func.sum(Document.file_size).label("total_size"),
        )
        .where(Document.user_id == current_user.id)
        .group_by(Document.file_type)
    )

    by_type = [
        {
            "file_type": row.file_type,
            "count": row.count,
            "total_size": row.total_size or 0,
        }
        for row in type_result.all()
    ]

    # By status
    status_result = await db.execute(
        select(
            Document.status,
            func.count(Document.id).label("count"),
        )
        .where(Document.user_id == current_user.id)
        .group_by(Document.status)
    )

    by_status = [
        {"status": row.status.value if hasattr(row.status, 'value') else str(row.status), "count": row.count}
        for row in status_result.all()
    ]

    return {"by_type": by_type, "by_status": by_status}
