"""
Studable API — Matching WebSocket endpoint (Phase 5).

Endpoint: GET /api/v1/ws/matching?ticket=<ticket>&token=<jwt>

Provides low-latency bi-directional real-time matching updates:
- matching.status
- matching.queued
- matching.found
- matching.accepted
- matching.peer_accepted
- matching.rejected
- matching.expired
- matching.completed
- matching.cancelled
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
from app.services.matching_service import cancel_queue, get_match_status

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Matching WebSocket"])


@router.websocket("/ws/matching")
async def matching_websocket(
    websocket: WebSocket,
    ticket: Optional[str] = Query(None, description="Short-lived opaque WS ticket"),
    token: Optional[str] = Query(None, description="JWT access token (fallback)"),
    redis: Redis = Depends(get_redis),
) -> None:
    """Real-time matching lifecycle WebSocket."""
    # ── 1. Authenticate ───────────────────────────────────────────────────────
    user_id: Optional[str] = None
    if ticket:
        try:
            cached_uid = await redis.get(f"ws:ticket:{ticket}")
            if cached_uid:
                if isinstance(cached_uid, bytes):
                    cached_uid = cached_uid.decode("utf-8")
                user_id = cached_uid
                await redis.delete(f"ws:ticket:{ticket}")
        except Exception as exc:
            logger.warning("Redis error checking ticket: %s", exc)

    if not user_id and token:
        try:
            payload = decode_access_token(token)
            user_id = payload.get("sub")
        except Exception:
            user_id = None

    if not user_id:
        await websocket.close(code=1008, reason="Invalid or expired ticket/token")
        return

    # ── 2. Accept & Initial State Snapshot ────────────────────────────────────
    await websocket.accept()
    logger.info("Matching WS connected: user=%s", user_id)

    db = SessionLocal()
    try:
        initial_status = await get_match_status(redis, db, user_id)
        await websocket.send_json({
            "type": "matching.status",
            "user_id": user_id,
            "data": initial_status,
        })
    finally:
        db.close()

    # ── 3. Subscribe to Pub/Sub Channel ───────────────────────────────────────
    pubsub_task: Optional[asyncio.Task] = None

    async def _pubsub_forwarder():
        pubsub = redis.pubsub()
        channel = f"channel:user:{user_id}"
        try:
            await pubsub.subscribe(channel)
            async for message in pubsub.listen():
                if message and message.get("type") == "message":
                    raw_data = message.get("data")
                    if isinstance(raw_data, bytes):
                        raw_data = raw_data.decode("utf-8")
                    if raw_data:
                        await websocket.send_text(raw_data)
        except asyncio.CancelledError:
            pass
        except Exception as p_exc:
            logger.debug("Pubsub forwarder error: %s", p_exc)
        finally:
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.close()
            except Exception:
                pass

    pubsub_task = asyncio.create_task(_pubsub_forwarder())

    # ── 4. Message loop ───────────────────────────────────────────────────────
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type")
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            elif msg_type == "cancel":
                db_session = SessionLocal()
                try:
                    await cancel_queue(redis, db_session, user_id)
                finally:
                    db_session.close()

    except WebSocketDisconnect:
        logger.info("Matching WS disconnected: user=%s", user_id)
    except Exception as exc:
        logger.warning("Matching WS unexpected error: user=%s: %s", user_id, exc)
    finally:
        if pubsub_task and not pubsub_task.done():
            pubsub_task.cancel()
