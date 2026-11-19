"""
Studable API — Redis connection management.

Provides an async Redis client using redis.asyncio with connection pooling.
Handles graceful degradation when Redis is unavailable.
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator

import redis.asyncio as aioredis
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Connection pool (created once at module load) ─────────────────────────────
_pool: aioredis.ConnectionPool | None = None


def get_redis_pool() -> aioredis.ConnectionPool:
    """Return (and lazily create) the shared connection pool."""
    global _pool
    if _pool is None:
        _pool = aioredis.ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=20,
            decode_responses=True,
        )
    return _pool


def get_redis_client() -> Redis:
    """Return an async Redis client backed by the shared pool."""
    return aioredis.Redis(connection_pool=get_redis_pool())


async def get_redis() -> AsyncGenerator[Redis, None]:
    """
    FastAPI dependency: yields an async Redis client.

    Does NOT close the client on exit — the pool is long-lived.
    Callers should not close the client either.
    """
    client = get_redis_client()
    try:
        yield client
    finally:
        # Connection is returned to the pool automatically; no explicit close needed.
        pass


async def check_redis_connection() -> bool:
    """
    Ping Redis and return True if reachable, False otherwise.

    Safe to call from health-check endpoints — never raises.
    """
    try:
        client = get_redis_client()
        pong = await client.ping()
        return bool(pong)
    except RedisError as exc:
        logger.warning("Redis health check failed: %s", exc)
        return False
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Unexpected error during Redis health check: %s", exc)
        return False


async def close_redis_pool() -> None:
    """
    Gracefully close the shared connection pool.

    Call this during application shutdown (lifespan event).
    """
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None
        logger.info("Redis connection pool closed.")
