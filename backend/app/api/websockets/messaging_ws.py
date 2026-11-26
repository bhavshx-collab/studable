"""
Studable API — Messaging WebSocket endpoint (Phase 6).

Endpoint: GET /api/v1/ws/messaging?ticket=<ticket>&token=<jwt>

Message protocol (JSON)
-----------------------
Client → Server:
  {"type": "message.send",  "conversation_id": "...", "content": "..."}
  {"type": "typing.start",  "conversation_id": "..."}
  {"type": "typing.stop",   "conversation_id": "..."}
  {"type": "message.read",  "conversation_id": "..."}
  {"type": "heartbeat"}

Server → Client (forwarded from Redis Pub/Sub or direct):
  {"type": "messaging.connected", "user_id": "..."}
  {"type": "message.new",         "conversation_id": "...", "message": {...}}
  {"type": "message.read",        "conversation_id": "...", "reader_id": "..."}
  {"type": "typing.start",        "conversation_id": "...", "user_id": "..."}
  {"type": "typing.stop",         "conversation_id": "...", "user_id": "..."}
  {"type": "conversation.ended",  "conversation_id": "...", "ended_by": "..."}
  {"type": "heartbeat.ack"}
  {"type": "error",               "code": "...", "detail": "..."}
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.redis import get_redis
from app.core.security import decode_access_token
from app.services.messaging_service import (
    end_conversation,
    get_conversation_or_none,
    mark_message_delivered,
    mark_messages_read,
    publish_typing,
    send_message,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Messaging WebSocket"])

_USER_CHANNEL = "channel:user:{}"


@router.websocket("/ws/messaging")
async def messaging_websocket(
    websocket: WebSocket,
    ticket: Optional[str] = Query(None),
    token: Optional[str] = Query(None),
    redis: Redis = Depends(get_redis),
) -> None:
    """Real-time messaging WebSocket, authenticated via ticket or JWT."""

    # ── 1. Authenticate ──────────────────────────────────────────────────────
    user_id: Optional[str] = None

    if ticket:
        try:
            cached = await redis.get(f"ws:ticket:{ticket}")
            if cached:
                user_id = cached.decode("utf-8") if isinstance(cached, bytes) else cached
                await redis.delete(f"ws:ticket:{ticket}")
        except Exception as exc:
            logger.warning("Redis error checking ticket: %s", exc)

    if not user_id and token:
        try:
            payload = decode_access_token(token)
            user_id = payload.get("sub")
        except Exception:
            pass

    if not user_id:
        await websocket.close(code=1008)
        return

    # Origin verification in production
    origin = websocket.headers.get("origin")
    if origin and settings.ENVIRONMENT == "production":
        if origin not in settings.CORS_ORIGINS:
            await websocket.close(code=1008)
            return

    # Concurrency limit check
    active_key = f"ws:active:messaging:{user_id}"
    try:
        active_count = await redis.incr(active_key)
        if active_count > settings.WS_MAX_CONNECTIONS_PER_USER:
            await redis.decr(active_key)
            await websocket.close(code=1008)
            return
    except Exception:
        pass

    await websocket.accept()
    await websocket.send_text(json.dumps({"type": "messaging.connected", "user_id": user_id}))

    # ── 2. Subscribe to Redis Pub/Sub for this user ───────────────────────────
    pubsub = redis.pubsub()
    await pubsub.subscribe(_USER_CHANNEL.format(user_id))

    async def _pubsub_forwarder() -> None:
        try:
            async for raw_msg in pubsub.listen():
                if raw_msg["type"] != "message":
                    continue
                data = raw_msg.get("data")
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                try:
                    evt = json.loads(data)
                except Exception:
                    continue
                # Only forward messaging-relevant events
                if evt.get("type", "").startswith(("message.", "typing.", "conversation.")):
                    try:
                        await websocket.send_text(json.dumps(evt))
                    except Exception:
                        break
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.debug("Messaging pubsub forwarder error: %s", exc)

    forwarder_task = asyncio.create_task(_pubsub_forwarder())

    # ── 3. Main receive loop ─────────────────────────────────────────────────
    try:
        while True:
            try:
                raw = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=settings.HEARTBEAT_INTERVAL_SECONDS + 10,
                )
            except asyncio.TimeoutError:
                await websocket.close(code=1001)
                break

            try:
                msg = json.loads(raw)
            except Exception:
                await websocket.send_text(json.dumps({"type": "error", "code": "INVALID_JSON", "detail": "Invalid JSON"}))
                continue

            msg_type = msg.get("type", "")

            if msg_type == "heartbeat":
                await websocket.send_text(json.dumps({"type": "heartbeat.ack"}))

            elif msg_type == "message.send":
                conv_id = msg.get("conversation_id", "")
                content = msg.get("content", "")
                client_msg_id = msg.get("client_message_id")
                if not conv_id or not content:
                    await websocket.send_text(json.dumps({"type": "error", "code": "MISSING_FIELDS", "detail": "conversation_id and content required"}))
                    continue
                async with _db_session() as db:
                    result = await send_message(db, redis, conv_id, user_id, content, client_message_id=client_msg_id)
                if result is None:
                    await websocket.send_text(json.dumps({"type": "error", "code": "SEND_FAILED", "detail": "Could not send message"}))

            elif msg_type == "message.delivered":
                conv_id = msg.get("conversation_id", "")
                mid = msg.get("message_id", "")
                if conv_id and mid:
                    async with _db_session() as db:
                        await mark_message_delivered(db, redis, conv_id, mid, user_id)

            elif msg_type in ("typing.start", "typing.stop"):
                conv_id = msg.get("conversation_id", "")
                if conv_id:
                    async with _db_session() as db:
                        conv = get_conversation_or_none(db, conv_id, user_id)
                        if conv and conv.status == "active":
                            peer_id = (
                                conv.participant_b if conv.participant_a == user_id else conv.participant_a
                            )
                            if peer_id:
                                await publish_typing(redis, conv_id, user_id, peer_id, msg_type == "typing.start")

            elif msg_type == "message.read":
                conv_id = msg.get("conversation_id", "")
                if conv_id:
                    async with _db_session() as db:
                        await mark_messages_read(db, redis, conv_id, user_id)

            else:
                await websocket.send_text(json.dumps({"type": "error", "code": "UNKNOWN_TYPE", "detail": f"Unknown message type: {msg_type}"}))

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("Messaging WS error for user %s: %s", user_id, exc)
    finally:
        forwarder_task.cancel()
        try:
            await redis.decr(active_key)
        except Exception:
            pass
        try:
            await pubsub.unsubscribe(_USER_CHANNEL.format(user_id))
            await pubsub.aclose()
        except Exception:
            pass


class _db_session:
    """Async context manager that provides a synchronous SQLAlchemy session."""

    def __init__(self):
        self._db = None

    async def __aenter__(self):
        self._db = SessionLocal()
        return self._db

    async def __aexit__(self, *_):
        if self._db:
            self._db.close()
