"""
Studable API — Presence service.

Manages real-time user presence state in Redis.

Redis key schema
----------------
  presence:user:{user_id}:state     STRING   e.g. "AVAILABLE"       TTL = PRESENCE_TTL_SECONDS
  presence:user:{user_id}:sessions  SET      {session_id, ...}      no TTL (membership managed explicitly)

State machine
-------------
  OFFLINE → ONLINE
  ONLINE  → AVAILABLE | BUSY | OFFLINE
  AVAILABLE → BUSY | MATCHING | OFFLINE | ONLINE
  BUSY    → AVAILABLE | OFFLINE | ONLINE
  MATCHING → IN_CONVERSATION | AVAILABLE | OFFLINE
  IN_CONVERSATION → AVAILABLE | OFFLINE

Transitions marked as BACKEND_ONLY cannot be initiated by a WebSocket client message.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Dict, List, Optional, Set

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── State machine ─────────────────────────────────────────────────────────────


class PresenceStatus(str, Enum):
    OFFLINE = "OFFLINE"
    ONLINE = "ONLINE"
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    MATCHING = "MATCHING"
    IN_CONVERSATION = "IN_CONVERSATION"


# Valid transitions: from_state -> set of allowed to_states
VALID_TRANSITIONS: Dict[PresenceStatus, Set[PresenceStatus]] = {
    PresenceStatus.OFFLINE: {PresenceStatus.ONLINE},
    PresenceStatus.ONLINE: {PresenceStatus.AVAILABLE, PresenceStatus.BUSY, PresenceStatus.OFFLINE},
    PresenceStatus.AVAILABLE: {
        PresenceStatus.BUSY,
        PresenceStatus.MATCHING,
        PresenceStatus.OFFLINE,
        PresenceStatus.ONLINE,
    },
    PresenceStatus.BUSY: {
        PresenceStatus.AVAILABLE,
        PresenceStatus.OFFLINE,
        PresenceStatus.ONLINE,
    },
    PresenceStatus.MATCHING: {
        PresenceStatus.IN_CONVERSATION,
        PresenceStatus.AVAILABLE,
        PresenceStatus.OFFLINE,
    },
    PresenceStatus.IN_CONVERSATION: {
        PresenceStatus.AVAILABLE,
        PresenceStatus.OFFLINE,
    },
}

# States that can only be set by trusted backend operations (not WebSocket clients).
BACKEND_ONLY_STATES: Set[PresenceStatus] = {
    PresenceStatus.MATCHING,
    PresenceStatus.IN_CONVERSATION,
}

# ── Redis key helpers ─────────────────────────────────────────────────────────


def _state_key(user_id: str) -> str:
    return f"presence:user:{user_id}:state"


def _sessions_key(user_id: str) -> str:
    return f"presence:user:{user_id}:sessions"


def _session_lease_key(session_id: str) -> str:
    return f"presence:session:{session_id}:lease"


# ── Core presence operations ───────────────────────────────────────────────────


async def get_presence(redis: Redis, user_id: str) -> PresenceStatus:
    """
    Return the current presence state for *user_id*.

    Returns OFFLINE if the key is missing (expired or never set).
    Returns OFFLINE on Redis failure (graceful degradation).
    """
    try:
        raw = await redis.get(_state_key(user_id))
        if raw is None:
            return PresenceStatus.OFFLINE
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        try:
            return PresenceStatus(raw)
        except ValueError:
            logger.warning("Unknown presence state '%s' for user %s", raw, user_id)
            return PresenceStatus.OFFLINE
    except RedisError as exc:
        logger.warning("Redis error in get_presence for %s: %s", user_id, exc)
        return PresenceStatus.OFFLINE


async def set_presence(
    redis: Redis,
    user_id: str,
    new_status: PresenceStatus,
    *,
    ttl: Optional[int] = None,
) -> bool:
    """
    Unconditionally set the presence state for *user_id* (backend-initiated).

    Use ``set_presence_validated`` for client-initiated transitions.
    Returns True on success, False on Redis failure.
    """
    effective_ttl = ttl if ttl is not None else settings.PRESENCE_TTL_SECONDS
    try:
        if new_status == PresenceStatus.OFFLINE:
            # Remove the state key when going offline.
            await redis.delete(_state_key(user_id))
        else:
            await redis.set(_state_key(user_id), new_status.value, ex=effective_ttl)
        return True
    except RedisError as exc:
        logger.warning("Redis error in set_presence for %s: %s", user_id, exc)
        return False


async def set_presence_validated(
    redis: Redis,
    user_id: str,
    new_status: PresenceStatus,
    *,
    allow_backend_only: bool = False,
    ttl: Optional[int] = None,
) -> tuple[bool, str]:
    """
    Set presence state with transition validation.

    Args:
        allow_backend_only: If False (default), reject BACKEND_ONLY_STATES.

    Returns:
        (success: bool, error_message: str)
        error_message is empty on success.
    """
    if new_status in BACKEND_ONLY_STATES and not allow_backend_only:
        return False, f"State '{new_status.value}' can only be set by backend operations."

    current = await get_presence(redis, user_id)
    allowed = VALID_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        return False, (
            f"Transition from '{current.value}' to '{new_status.value}' is not allowed."
        )

    ok = await set_presence(redis, user_id, new_status, ttl=ttl)
    if not ok:
        return False, "Redis write failed."
    return True, ""


# ── Session tracking ──────────────────────────────────────────────────────────


async def register_session(
    redis: Redis,
    user_id: str,
    session_id: str,
    *,
    ttl: Optional[int] = None,
) -> bool:
    """
    Add *session_id* to the user's active session set and set state to ONLINE.

    Also sets an expiring session lease key to guard against crashed sessions.
    If the user is already in a non-OFFLINE state (e.g. MATCHING), preserve that state.
    """
    try:
        effective_ttl = ttl if ttl is not None else settings.PRESENCE_TTL_SECONDS
        await redis.sadd(_sessions_key(user_id), session_id)
        # Set per-session lease with TTL
        await redis.set(_session_lease_key(session_id), user_id, ex=effective_ttl)

        current = await get_presence(redis, user_id)
        if current == PresenceStatus.OFFLINE:
            # First session — go ONLINE.
            await set_presence(redis, user_id, PresenceStatus.ONLINE, ttl=effective_ttl)
        else:
            # Additional session or re-entry — refresh TTL without clobbering active state.
            await redis.expire(_state_key(user_id), effective_ttl)
        return True
    except RedisError as exc:
        logger.warning("Redis error in register_session for %s/%s: %s", user_id, session_id, exc)
        return False


async def unregister_session(
    redis: Redis,
    user_id: str,
    session_id: str,
) -> bool:
    """
    Remove *session_id* from the user's active session set and delete its lease.

    If no sessions remain, mark the user OFFLINE (remove state key).
    Returns True if the user is now offline, False if sessions remain.
    """
    try:
        await redis.delete(_session_lease_key(session_id))
        await redis.srem(_sessions_key(user_id), session_id)
        remaining = await redis.scard(_sessions_key(user_id))
        if remaining == 0:
            await redis.delete(_sessions_key(user_id))
            await set_presence(redis, user_id, PresenceStatus.OFFLINE)
            return True  # user is now offline
        return False  # still has active sessions
    except RedisError as exc:
        logger.warning("Redis error in unregister_session for %s/%s: %s", user_id, session_id, exc)
        return False


async def refresh_ttl(
    redis: Redis,
    user_id: str,
    session_id: str,
    *,
    ttl: Optional[int] = None,
) -> bool:
    """
    Heartbeat handler: refresh the TTL on the state key and session lease key.

    Returns True if the session is still active, False if it's unknown.
    """
    try:
        effective_ttl = ttl if ttl is not None else settings.PRESENCE_TTL_SECONDS
        is_member = await redis.sismember(_sessions_key(user_id), session_id)
        if not is_member:
            return False
        await redis.set(_session_lease_key(session_id), user_id, ex=effective_ttl)
        await redis.expire(_state_key(user_id), effective_ttl)
        return True
    except RedisError as exc:
        logger.warning("Redis error in refresh_ttl for %s/%s: %s", user_id, session_id, exc)
        return False


async def cleanup_stale_sessions(redis: Redis, user_id: str) -> int:
    """
    Clean up expired session leases for *user_id*.

    If any session in the sessions set lacks an active lease key, remove it.
    If no valid sessions remain, mark user OFFLINE.
    Returns the number of pruned stale sessions.
    """
    try:
        sessions = await redis.smembers(_sessions_key(user_id))
        if not sessions:
            return 0

        pruned = 0
        for sid in sessions:
            if isinstance(sid, bytes):
                sid = sid.decode("utf-8")
            lease_exists = await redis.exists(_session_lease_key(sid))
            if not lease_exists:
                await redis.srem(_sessions_key(user_id), sid)
                pruned += 1

        remaining = await redis.scard(_sessions_key(user_id))
        if remaining == 0:
            await redis.delete(_sessions_key(user_id))
            await set_presence(redis, user_id, PresenceStatus.OFFLINE)

        return pruned
    except RedisError as exc:
        logger.warning("Redis error in cleanup_stale_sessions for %s: %s", user_id, exc)
        return 0


async def get_session_count(redis: Redis, user_id: str) -> int:
    """Return the number of active sessions for *user_id*."""
    try:
        return await redis.scard(_sessions_key(user_id))
    except RedisError:
        return 0


# ── Bulk queries ──────────────────────────────────────────────────────────────


async def get_online_count(redis: Redis) -> int:
    """
    Return the approximate count of non-OFFLINE users.

    Scans ``presence:user:*:state`` keys and counts non-OFFLINE values.
    Returns 0 on Redis failure (graceful degradation).
    """
    try:
        count = 0
        async for key in redis.scan_iter("presence:user:*:state", count=200):
            val = await redis.get(key)
            if isinstance(val, bytes):
                val = val.decode("utf-8")
            if val and val != PresenceStatus.OFFLINE.value:
                count += 1
        return count
    except RedisError as exc:
        logger.warning("Redis error in get_online_count: %s", exc)
        return 0


async def get_online_users(redis: Redis, limit: int = 100) -> List[str]:
    """
    Return up to *limit* user IDs that are non-OFFLINE.

    Returns empty list on Redis failure.
    """
    try:
        results: List[str] = []
        async for key in redis.scan_iter("presence:user:*:state", count=200):
            if len(results) >= limit:
                break
            if isinstance(key, bytes):
                key = key.decode("utf-8")
            val = await redis.get(key)
            if isinstance(val, bytes):
                val = val.decode("utf-8")
            if val and val != PresenceStatus.OFFLINE.value:
                # Key format: presence:user:{user_id}:state
                parts = key.split(":")
                if len(parts) == 4:
                    results.append(parts[2])
        return results
    except RedisError as exc:
        logger.warning("Redis error in get_online_users: %s", exc)
        return []


async def get_available_users(redis: Redis, limit: int = 100) -> List[str]:
    """
    Return up to *limit* user IDs in AVAILABLE state.

    Returns empty list on Redis failure.
    """
    try:
        results: List[str] = []
        async for key in redis.scan_iter("presence:user:*:state", count=200):
            if len(results) >= limit:
                break
            if isinstance(key, bytes):
                key = key.decode("utf-8")
            val = await redis.get(key)
            if isinstance(val, bytes):
                val = val.decode("utf-8")
            if val == PresenceStatus.AVAILABLE.value:
                parts = key.split(":")
                if len(parts) == 4:
                    results.append(parts[2])
        return results
    except RedisError as exc:
        logger.warning("Redis error in get_available_users: %s", exc)
        return []
