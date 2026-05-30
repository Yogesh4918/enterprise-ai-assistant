"""Analytics service — usage statistics and conversation insights."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.chat import Conversation, Message, MessageRole
from app.models.document import Document, DocumentStatus


async def get_usage_stats(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """Get usage statistics for a user."""
    # Total conversations
    conv_count = await db.execute(
        select(func.count(Conversation.id)).where(Conversation.user_id == user_id)
    )
    total_conversations = conv_count.scalar() or 0

    # Total messages
    msg_count = await db.execute(
        select(func.count(Message.id))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Conversation.user_id == user_id)
    )
    total_messages = msg_count.scalar() or 0

    # Total documents
    doc_count = await db.execute(
        select(func.count(Document.id)).where(Document.user_id == user_id)
    )
    total_documents = doc_count.scalar() or 0

    # Indexed documents
    indexed_count = await db.execute(
        select(func.count(Document.id)).where(
            Document.user_id == user_id,
            Document.status == DocumentStatus.INDEXED,
        )
    )
    indexed_documents = indexed_count.scalar() or 0

    # Messages in last 7 days
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent_msg_count = await db.execute(
        select(func.count(Message.id))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Conversation.user_id == user_id,
            Message.created_at >= week_ago,
        )
    )
    recent_messages = recent_msg_count.scalar() or 0

    # Average confidence score
    avg_confidence = await db.execute(
        select(func.avg(Message.confidence_score))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Conversation.user_id == user_id,
            Message.confidence_score.isnot(None),
        )
    )
    avg_conf = avg_confidence.scalar()

    return {
        "total_conversations": total_conversations,
        "total_messages": total_messages,
        "total_documents": total_documents,
        "indexed_documents": indexed_documents,
        "recent_messages_7d": recent_messages,
        "average_confidence_score": round(avg_conf, 3) if avg_conf else None,
    }


async def get_admin_stats(db: AsyncSession) -> dict:
    """Get system-wide statistics (admin only)."""
    user_count = await db.execute(select(func.count(User.id)))
    total_users = user_count.scalar() or 0

    conv_count = await db.execute(select(func.count(Conversation.id)))
    total_conversations = conv_count.scalar() or 0

    msg_count = await db.execute(select(func.count(Message.id)))
    total_messages = msg_count.scalar() or 0

    doc_count = await db.execute(select(func.count(Document.id)))
    total_documents = doc_count.scalar() or 0

    return {
        "total_users": total_users,
        "total_conversations": total_conversations,
        "total_messages": total_messages,
        "total_documents": total_documents,
    }
