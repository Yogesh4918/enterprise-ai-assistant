"""Chat service — conversation and message management + RAG orchestration."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models.chat import Conversation, Message, MessageRole
from app.rag.chain import RAGChain
from app.rag.retrieval import HybridRetriever
from app.rag.memory import ConversationMemory

logger = logging.getLogger(__name__)
settings = get_settings()


# ── Conversation CRUD ──────────────────────────────────────────────────
async def create_conversation(
    db: AsyncSession,
    user_id: uuid.UUID,
    title: str = "New Chat",
) -> Conversation:
    """Create a new conversation for the user."""
    conv = Conversation(
        id=uuid.uuid4(),
        user_id=user_id,
        title=title,
    )
    db.add(conv)
    await db.flush()
    return conv


async def get_conversations(
    db: AsyncSession,
    user_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
) -> list[Conversation]:
    """List conversations for a user, most recent first."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(desc(Conversation.updated_at))
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_conversation_with_messages(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Conversation | None:
    """Fetch a conversation with all its messages."""
    result = await db.execute(
        select(Conversation)
        .where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        .options(selectinload(Conversation.messages))
    )
    return result.scalar_one_or_none()


async def delete_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """Delete a conversation and its messages. Returns True if found."""
    conv = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    conversation = conv.scalar_one_or_none()
    if conversation is None:
        return False
    await db.delete(conversation)
    await db.flush()
    return True


async def update_conversation_title(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    title: str,
) -> Conversation | None:
    """Rename a conversation."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    conv = result.scalar_one_or_none()
    if conv is None:
        return None
    conv.title = title
    conv.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return conv


# ── Message management ─────────────────────────────────────────────────
async def add_message(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    role: MessageRole,
    content: str,
    citations: list | None = None,
    confidence_score: float | None = None,
    language: str | None = None,
) -> Message:
    """Persist a message to the database."""
    msg = Message(
        id=uuid.uuid4(),
        conversation_id=conversation_id,
        role=role,
        content=content,
        citations=citations,
        confidence_score=confidence_score,
        language=language,
    )
    db.add(msg)
    await db.flush()

    # Update conversation timestamp
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if conv:
        conv.updated_at = datetime.now(timezone.utc)
        # Auto-title from first user message
        if role == MessageRole.USER and conv.title == "New Chat":
            conv.title = content[:80].strip() + ("..." if len(content) > 80 else "")
        await db.flush()

    return msg


# ── Agent-powered message processing ──────────────────────────────────
async def process_message(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    content: str,
    collection_name: str | None = None,
    use_agents: bool = True,
) -> dict:
    """
    Process a user message through the LangGraph agent pipeline.

    The agent graph classifies intent and routes to the appropriate handler:
    - question → retrieve + RAG chain
    - summarize → retrieve + summarization agent
    - translate → translation agent
    - chat → direct LLM response

    Falls back to direct RAG chain if agents encounter errors.

    Returns dict with: answer, citations, confidence_score, intent
    """
    # 1. Save user message
    await add_message(db, conversation_id, MessageRole.USER, content)

    # 2. Get chat history from memory
    memory = ConversationMemory()
    history = await memory.get_history(str(conversation_id), limit=10)

    target_collection = collection_name or f"user_{user_id}"

    if use_agents:
        try:
            result = await _process_with_agents(
                content, target_collection, history
            )
        except Exception as e:
            logger.warning(f"Agent pipeline failed, falling back to direct RAG: {e}")
            result = await _process_with_rag(
                content, target_collection, history
            )
    else:
        result = await _process_with_rag(content, target_collection, history)

    # 3. Save assistant message
    await add_message(
        db,
        conversation_id,
        MessageRole.ASSISTANT,
        result["answer"],
        citations=result.get("citations"),
        confidence_score=result.get("confidence_score"),
    )

    # 4. Update memory
    await memory.add_message(str(conversation_id), "user", content)
    await memory.add_message(str(conversation_id), "assistant", result["answer"])

    return result


async def _process_with_agents(
    content: str,
    collection: str,
    history: str,
) -> dict:
    """Process through the LangGraph agent graph."""
    from app.agents.graph import agent_graph

    state = {
        "query": content,
        "collection": collection,
        "chat_history": history,
    }

    result_state = await agent_graph.ainvoke(state)

    response = result_state.get("response")
    if response is None:
        raise ValueError("Agent graph returned no response")

    # Normalize the response to a dict
    answer = getattr(response, "answer", str(response))
    confidence = getattr(response, "confidence", None)
    citations_raw = getattr(response, "citations", [])
    metadata = getattr(response, "metadata", {})

    citations = []
    if citations_raw:
        for i, c in enumerate(citations_raw):
            if isinstance(c, dict):
                citations.append(c)
            else:
                citations.append({
                    "index": i,
                    "source": getattr(c, "source", "document"),
                    "chunk_text": getattr(c, "text", str(c)),
                    "relevance_score": getattr(c, "score", 0.5),
                })

    return {
        "answer": answer,
        "citations": citations or None,
        "confidence_score": confidence,
        "intent": result_state.get("intent", "question"),
        "metadata": metadata,
    }


async def _process_with_rag(
    content: str,
    collection: str,
    history: str,
) -> dict:
    """Direct RAG chain fallback (no agent routing)."""
    retriever = HybridRetriever()
    retrieved_docs = await retriever.retrieve(content, collection)

    rag_chain = RAGChain()
    result = await rag_chain.generate(
        query=content,
        context_docs=retrieved_docs,
        chat_history=history,
    )

    return result


async def stream_message(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    content: str,
    collection_name: str | None = None,
) -> AsyncGenerator[dict, None]:
    """
    Stream a RAG-powered response token by token.

    Yields dicts with type: "token" | "citation" | "confidence" | "done"
    """
    # Save user message
    await add_message(db, conversation_id, MessageRole.USER, content)

    # Get chat history
    memory = ConversationMemory()
    history = await memory.get_history(str(conversation_id), limit=10)

    # Retrieve relevant documents
    retriever = HybridRetriever()
    target_collection = collection_name or f"user_{user_id}"
    retrieved_docs = await retriever.retrieve(content, target_collection)

    # Stream response
    rag_chain = RAGChain()
    full_response = ""
    citations = []

    async for event in rag_chain.stream_generate(
        query=content,
        context_docs=retrieved_docs,
        chat_history=history,
    ):
        if event["type"] == "token":
            full_response += event["data"]
            yield event
        elif event["type"] == "citation":
            citations.append(event["data"])
            yield event
        elif event["type"] == "confidence":
            yield event

    # Save completed assistant message
    confidence = None
    if retrieved_docs:
        scores = [d.get("score", 0) for d in retrieved_docs if d.get("score")]
        confidence = sum(scores) / len(scores) if scores else None

    await add_message(
        db,
        conversation_id,
        MessageRole.ASSISTANT,
        full_response,
        citations=citations or None,
        confidence_score=confidence,
    )

    # Update memory
    await memory.add_message(str(conversation_id), "user", content)
    await memory.add_message(str(conversation_id), "assistant", full_response)

    yield {"type": "done", "data": None}
