"""
Studable API — WebSocket Ticket Route.

Generates short-lived, single-use authentication tickets for WebSocket connections.
This prevents long-lived JWT access tokens from being exposed in browser logs,
proxy access logs, or query strings.
"""

from __future__ import annotations

import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis

from app.core.dependencies import get_current_user
from app.core.redis import get_redis
from app.models.user import User

router = APIRouter(prefix="/ws", tags=["WebSocket Tickets"])

TICKET_TTL_SECONDS = 30  # Ticket expires after 30 seconds if unused


@router.post("/ticket", summary="Obtain a short-lived WebSocket ticket")
async def create_ws_ticket(
    current_user: User = Depends(get_current_user),
    redis: Redis = Depends(get_redis),
) -> dict:
    """
    Generate an opaque 32-byte ticket stored in Redis with a 30s TTL.
    Client exchanges this ticket via `?ticket=<opaque_token>` on WS upgrade.
    Single-use: deleted from Redis upon first successful WS connection.
    """
    ticket = secrets.token_urlsafe(32)
    ticket_key = f"ws:ticket:{ticket}"

    try:
        await redis.set(ticket_key, current_user.id, ex=TICKET_TTL_SECONDS)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to generate ticket due to cache unavailable.",
        ) from exc

    return {
        "ticket": ticket,
        "expires_in": TICKET_TTL_SECONDS,
    }
