"""
Studable API — Presence WebSocket endpoint.

Endpoint:  GET /api/v1/ws/presence?token=<access_token>

Authentication is via the ``token`` query parameter because browsers
cannot attach Authorization headers to WebSocket upgrade requests.

Message protocol (JSON)
-----------------------
Client → Server:
  {"type": "heartbeat"}
  {"type": "set_status", "status": "AVAILABLE" | "BUSY"}

Server → Client:
  {"type": "presence.connected",   "user_id": "...", "status": "ONLINE", "heartbeat_interval": 30}
  {"type": "heartbeat.ack",        "user_id": "...", "status": "<current>"}
  {"type": "presence.updated",     "user_id": "...", "status": "<new>"}
  {"type": "error",                "code": "...",    "detail": "..."}

Security
--------
- MATCHING and IN_CONVERSATION cannot be set via WebSocket (BACKEND_ONLY).
- All transitions are validated by the state machine.
- Expired or invalid tokens are rejected with WS close code 1008.
"""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
from collections import defaultdict
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from jose import JWTError
from redis.asyncio import Redis

from app.core.config import settings
from app.core.redis import get_redis
from app.core.security import decode_access_token
from app.services.presence_service import (
    PresenceStatus,
    cleanup_stale_sessions,
    get_presence,
    refresh_ttl,
    register_session,
    set_presence_validated,
    unregister_session,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Presence WebSocket"])

# ── Connection manager ────────────────────────────────────────────────────────


class ConnectionManager:
    """Tracks active WebSocket connections by user_id."""

    def __init__(self) -> None:
        # user_id -> list of (session_id, WebSocket)
        self._connections: Dict[str, List[tuple[str, WebSocket]]] = defaultdict(list)

    def add(self, user_id: str, session_id: str, ws: WebSocket) -> None:
        self._connections[user_id].append((session_id, ws))

    def remove(self, user_id: str, session_id: str) -> None:
        conns = self._connections.get(user_id, [])
        self._connections[user_id] = [(sid, ws) for sid, ws in conns if sid != session_id]
        if not self._connections[user_id]:
            del self._connections[user_id]

    async def broadcast_to_user(self, user_id: str, message: dict) -> None:
        """Send *message* to all active connections for *user_id*."""
        conns = self._connections.get(user_id, [])
        for _, ws in conns:
            try:
                await ws.send_json(message)
            except Exception:  # pylint: disable=broad-except
                pass

    def active_user_count(self) -> int:
        return len(self._connections)


manager = ConnectionManager()

# ── Helper ────────────────────────────────────────────────────────────────────


def _error(code: str, detail: str) -> dict:
    return {"type": "error", "code": code, "detail": detail}


# ── WebSocket endpoint ────────────────────────────────────────────────────────


@router.websocket("/ws/presence")
async def presence_websocket(
    websocket: WebSocket,
    ticket: Optional[str] = Query(None, description="Short-lived opaque WS ticket"),
    token: Optional[str] = Query(None, description="JWT access token (fallback)"),
    redis: Redis = Depends(get_redis),
) -> None:
    """
    Real-time presence WebSocket.

    Authenticate with ``?ticket=<ticket>`` (preferred) or ``?token=<access_token>`` (legacy/test).
    """
    # ── 1. Authenticate ───────────────────────────────────────────────────────
    user_id: Optional[str] = None
    if ticket:
        try:
            cached_uid = await redis.get(f"ws:ticket:{ticket}")
            if cached_uid:
                if isinstance(cached_uid, bytes):
                    cached_uid = cached_uid.decode("utf-8")
                user_id = cached_uid
                # Single-use: delete immediately
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

    origin = websocket.headers.get("origin")
    if origin and settings.ENVIRONMENT == "production":
        if origin not in settings.CORS_ORIGINS:
            await websocket.close(code=1008, reason="Origin not allowed")
            return

    # ── 2. Accept connection ──────────────────────────────────────────────────
    await websocket.accept()
    session_id = secrets.token_hex(16)

    # ── 3. Register session in Redis ──────────────────────────────────────────
    await register_session(redis, user_id, session_id)
    # Clean up any stale sessions left over from crashed tabs/devices
    await cleanup_stale_sessions(redis, user_id)
    manager.add(user_id, session_id, websocket)

    current_status = await get_presence(redis, user_id)
    await websocket.send_json({
        "type": "presence.connected",
        "user_id": user_id,
        "status": current_status.value,
        "heartbeat_interval": settings.PRESENCE_HEARTBEAT_INTERVAL,
    })
    logger.info("WS presence connected: user=%s session=%s", user_id, session_id)

    # ── 4. Pub/Sub listener for multi-worker event delivery ───────────────────
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
            logger.debug("PubSub forwarder ended for user %s: %s", user_id, p_exc)
        finally:
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.close()
            except Exception:
                pass

    try:
        pubsub_task = asyncio.create_task(_pubsub_forwarder())
    except Exception as exc:
        logger.warning("Could not start PubSub listener for user %s: %s", user_id, exc)

    # ── 5. Message loop ───────────────────────────────────────────────────────
    try:
        while True:
            try:
                raw = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=settings.PRESENCE_TTL_SECONDS * 2,
                )
            except asyncio.TimeoutError:
                # Client has not sent a heartbeat in too long — close gracefully.
                logger.info(
                    "WS presence timeout: user=%s session=%s", user_id, session_id
                )
                await websocket.close(code=1001, reason="Heartbeat timeout")
                break

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json(
                    _error("invalid_json", "Message must be valid JSON.")
                )
                continue

            msg_type = data.get("type")

            if msg_type == "heartbeat":
                ok = await refresh_ttl(redis, user_id, session_id)
                status_now = await get_presence(redis, user_id)
                await websocket.send_json({
                    "type": "heartbeat.ack",
                    "user_id": user_id,
                    "status": status_now.value,
                })
                if not ok:
                    # Session was not in Redis (e.g., after Redis restart) — re-register.
                    await register_session(redis, user_id, session_id)

            elif msg_type == "set_status":
                raw_status = data.get("status", "")
                try:
                    new_status = PresenceStatus(raw_status)
                except ValueError:
                    await websocket.send_json(
                        _error("invalid_status", f"Unknown status: '{raw_status}'")
                    )
                    continue

                success, error_msg = await set_presence_validated(
                    redis,
                    user_id,
                    new_status,
                    allow_backend_only=False,
                )
                if not success:
                    await websocket.send_json(_error("transition_rejected", error_msg))
                else:
                    await websocket.send_json({
                        "type": "presence.updated",
                        "user_id": user_id,
                        "status": new_status.value,
                    })
                    logger.info(
                        "WS presence updated: user=%s status=%s", user_id, new_status.value
                    )
            else:
                await websocket.send_json(
                    _error("unknown_type", f"Unknown message type: '{msg_type}'")
                )

    except WebSocketDisconnect:
        logger.info("WS presence disconnected: user=%s session=%s", user_id, session_id)
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("WS presence unexpected error: user=%s: %s", user_id, exc)
    finally:
        # Cancel Pub/Sub task
        if pubsub_task and not pubsub_task.done():
            pubsub_task.cancel()
        # ── 6. Clean up ───────────────────────────────────────────────────────
        manager.remove(user_id, session_id)
        went_offline = await unregister_session(redis, user_id, session_id)
        if went_offline:
            logger.info("WS presence: user=%s is now OFFLINE", user_id)
