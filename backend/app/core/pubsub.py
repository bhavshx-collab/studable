"""
Studable API — Redis Pub/Sub helpers.

Used to deliver WebSocket events to users across multiple uvicorn workers.
Every worker subscribes to per-user channels and forwards matching events
to its locally connected WebSocket clients.

Channel naming
--------------
  channel:user:{user_id}   — per-user event fan-out channel

Message format (JSON)
---------------------
  Any dict that the recipient's WS layer can understand, e.g.:
    {"type": "matching.found", "match_id": "...", ...}
"""

from __future__ import annotations

import json
import logging
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


def _user_channel(user_id: str) -> str:
    return f"channel:user:{user_id}"


async def publish_to_user(redis: Redis, user_id: str, event: dict[str, Any]) -> bool:
    """
    Publish *event* to all workers listening for *user_id*.

    Returns True on success, False on Redis error (best-effort delivery).
    """
    try:
        payload = json.dumps(event, default=str)
        await redis.publish(_user_channel(user_id), payload)
        return True
    except RedisError as exc:
        logger.warning("pubsub publish failed for user %s: %s", user_id, exc)
        return False
