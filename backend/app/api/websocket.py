"""WebSocket endpoint for real-time streaming chat."""

from __future__ import annotations

import json
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import JWTError

from app.database import async_session_factory
from app.services.auth_service import decode_token, get_user_by_id
from app.services import chat_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["WebSocket"])


async def _authenticate_ws(websocket: WebSocket, token: str) -> uuid.UUID | None:
    """Validate JWT token for WebSocket connection. Returns user_id or None."""
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        return uuid.UUID(payload["sub"])
    except (JWTError, ValueError, KeyError):
        return None


@router.websocket("/ws/chat/{conversation_id}")
async def chat_websocket(
    websocket: WebSocket,
    conversation_id: uuid.UUID,
    token: str = Query(...),
):
    """
    Real-time streaming chat via WebSocket.

    Events sent to client:
    - {"type": "token", "data": "..."}       — streaming token
    - {"type": "citation", "data": {...}}     — citation object
    - {"type": "confidence", "data": 0.85}   — confidence score
    - {"type": "done", "data": null}          — stream complete
    - {"type": "error", "data": "..."}        — error message
    """
    # Authenticate
    user_id = await _authenticate_ws(websocket, token)
    if user_id is None:
        await websocket.close(code=1008, reason="Invalid authentication token")
        return

    await websocket.accept()
    logger.info(f"WebSocket connected: user={user_id}, conversation={conversation_id}")

    try:
        while True:
            # Receive message from client
            raw = await websocket.receive_text()

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "data": "Invalid JSON"})
                continue

            msg_type = data.get("type", "message")
            content = data.get("content", "").strip()

            if msg_type == "ping":
                await websocket.send_json({"type": "pong", "data": None})
                continue

            if not content:
                await websocket.send_json({"type": "error", "data": "Empty message"})
                continue

            # Stream RAG response
            async with async_session_factory() as db:
                try:
                    async for event in chat_service.stream_message(
                        db,
                        conversation_id=conversation_id,
                        user_id=user_id,
                        content=content,
                    ):
                        await websocket.send_json(event)
                    await db.commit()
                except Exception as e:
                    await db.rollback()
                    logger.error(f"Stream error: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "data": f"Processing error: {str(e)}",
                    })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: user={user_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except Exception:
            pass
