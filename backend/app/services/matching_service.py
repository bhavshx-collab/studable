"""
Studable API — Real-Time Matching Engine Service (Phase 5).

Provides queue management, compatibility scoring, atomic candidate reservation,
match proposal lifecycle, and Redis Pub/Sub event dispatch.

Queue Architecture:
-------------------
  matching:queue:random      ZSET   score = join_time (FIFO), member = user_id
  matching:queue:interest    ZSET   score = join_time, member = user_id
  matching:user:{uid}:request HASH   mode, status, joined_at, match_id
  matching:reserved:{uid}    STRING match_id (TTL = 45s)
  matching:match:{mid}       HASH   user1_id, user2_id, mode, status, score, expires_at
  matching:match:{mid}:acc   SET    accepted user_ids (TTL = 60s)
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.pubsub import publish_to_user
from app.models.block import Block
from app.models.conversation import Conversation
from app.models.match_request import MatchRequest
from app.models.user import User, UserInterest, UserLanguage
from app.services.presence_service import (
    PresenceStatus,
    get_presence,
    set_presence,
    set_presence_validated,
)

logger = logging.getLogger(__name__)

MATCH_TIMEOUT_SECONDS = 30
RESERVATION_TTL_SECONDS = 45
QUEUE_TTL_SECONDS = 600

QUEUE_RANDOM = "matching:queue:random"
QUEUE_INTEREST = "matching:queue:interest"


def _user_req_key(user_id: str) -> str:
    return f"matching:user:{user_id}:request"


def _reserved_key(user_id: str) -> str:
    return f"matching:reserved:{user_id}"


def _match_key(match_id: str) -> str:
    return f"matching:match:{match_id}"


def _match_accepted_key(match_id: str) -> str:
    return f"matching:match:{match_id}:accepted"


# ── Profile & Scoring Helpers ─────────────────────────────────────────────────


def format_peer_summary(user: User) -> dict[str, Any]:
    """Extract public profile attributes safe for match proposals."""
    return {
        "id": user.id,
        "displayName": user.display_name,
        "avatarUrl": user.avatar_url,
        "category": user.category,
        "headline": user.headline or "",
        "bio": user.bio or "",
        "skills": [s.skill for s in user.skills] if user.skills else [],
        "interests": [i.interest for i in user.interests] if user.interests else [],
        "languages": [l.language for l in user.languages] if user.languages else [],
        "connectionCount": len(user.sent_connections or []) + len(user.received_connections or []),
        "isVerified": user.is_verified,
        "role": user.role,
    }


def compute_interest_score(user1: User, user2: User) -> float:
    """
    Deterministic scoring algorithm for interest-based matching.

    Weights:
      - Shared interests: 3.0 points each
      - Common languages: 2.0 points each
      - Preferred audience match: 2.0 points
      - Category alignment: 1.0 point
    Returns a normalized float in [0.0, 100.0].
    """
    u1_interests = {i.interest.lower() for i in user1.interests} if user1.interests else set()
    u2_interests = {i.interest.lower() for i in user2.interests} if user2.interests else set()
    shared_interests = len(u1_interests & u2_interests)

    u1_langs = {l.language.lower() for l in user1.languages} if user1.languages else set()
    u2_langs = {l.language.lower() for l in user2.languages} if user2.languages else set()
    if user1.preferred_language:
        u1_langs.add(user1.preferred_language.lower())
    if user2.preferred_language:
        u2_langs.add(user2.preferred_language.lower())
    common_langs = len(u1_langs & u2_langs)

    audience_match = 0
    if user1.preferred_audience in ("Anyone", user2.category):
        audience_match += 1
    if user2.preferred_audience in ("Anyone", user1.category):
        audience_match += 1

    category_bonus = 1 if user1.category == user2.category else 0

    raw_score = (shared_interests * 3.0) + (common_langs * 2.0) + (audience_match * 1.5) + category_bonus
    # Normalize to 0-100 range with soft ceiling
    score = min(100.0, max(10.0, (raw_score / 15.0) * 100.0))
    return round(score, 1)


AUDIENCE_MAP: dict[str, set[str]] = {
    "Students": {"Student"},
    "Professionals": {"Working Professional", "Entrepreneur", "Mentor"},
    "Anyone": {"Student", "Working Professional", "Entrepreneur", "Mentor"},
}


def is_eligible_pair(db: Session, user1: User, user2: User, mode: str) -> bool:
    """Check blocking, suspension, discovery permissions, and audience constraints."""
    if user1.id == user2.id:
        return False
    if user1.is_suspended or user2.is_suspended:
        return False
    if user1.deleted_at or user2.deleted_at:
        return False

    if mode == "random":
        if not user1.allow_random_discovery or not user2.allow_random_discovery:
            return False

    # Check audience filter (Students, Professionals, Anyone)
    allowed_for_u1 = AUDIENCE_MAP.get(user1.preferred_audience, {user1.preferred_audience})
    if user2.category not in allowed_for_u1:
        return False

    allowed_for_u2 = AUDIENCE_MAP.get(user2.preferred_audience, {user2.preferred_audience})
    if user1.category not in allowed_for_u2:
        return False

    # Check mutual block records
    block = db.execute(
        select(Block).where(
            or_(
                (Block.blocker_id == user1.id) & (Block.blocked_id == user2.id),
                (Block.blocker_id == user2.id) & (Block.blocked_id == user1.id),
            )
        )
    ).first()
    if block is not None:
        return False

    return True


# ── Queue Operations ──────────────────────────────────────────────────────────


async def join_queue(
    redis: Redis,
    db: Session,
    user_id: str,
    mode: str,
) -> tuple[bool, str, dict[str, Any]]:
    """
    Join matching queue in 'random' or 'interest' mode.

    Sets presence to MATCHING, persists MatchRequest in PostgreSQL,
    and adds user_id to the Redis sorted set.
    """
    if mode not in ("random", "interest"):
        return False, f"Invalid matching mode '{mode}'. Use 'random' or 'interest'.", {}

    user = db.execute(
        select(User).options(
            joinedload(User.interests),
            joinedload(User.languages),
            joinedload(User.skills),
        ).where(User.id == user_id)
    ).unique().scalar_one_or_none()

    if not user:
        return False, "User not found.", {}
    if user.is_suspended:
        return False, "User account is suspended.", {}

    # Check if already reserved or in match
    reserved = await redis.get(_reserved_key(user_id))
    if reserved:
        return False, "User is currently in an active match proposal.", {}

    current_req = await redis.hgetall(_user_req_key(user_id))
    if current_req and current_req.get("status") == "QUEUED":
        return False, "User is already queued for matching.", {}

    # Transition presence to MATCHING (backend authorized)
    await set_presence(redis, user_id, PresenceStatus.MATCHING)

    now_ts = time.time()
    queue_key = QUEUE_RANDOM if mode == "random" else QUEUE_INTEREST

    # Atomically add to Redis queue
    await redis.zadd(queue_key, {user_id: now_ts})
    await redis.hset(
        _user_req_key(user_id),
        mapping={
            "mode": mode,
            "status": "QUEUED",
            "joined_at": str(now_ts),
            "match_id": "",
        },
    )
    await redis.expire(_user_req_key(user_id), QUEUE_TTL_SECONDS)

    # Persist in DB
    match_req = MatchRequest(
        user1_id=user_id,
        mode=mode,
        status="QUEUED",
    )
    db.add(match_req)
    db.commit()

    # Publish real-time event
    await publish_to_user(
        redis,
        user_id,
        {
            "type": "matching.queued",
            "mode": mode,
            "joined_at": now_ts,
        },
    )

    return True, "", {
        "status": "QUEUED",
        "mode": mode,
        "joined_at": now_ts,
    }


async def cancel_queue(
    redis: Redis,
    db: Session,
    user_id: str,
) -> tuple[bool, str]:
    """Leave matching queue and return to AVAILABLE presence."""
    # Remove from both queues
    await redis.zrem(QUEUE_RANDOM, user_id)
    await redis.zrem(QUEUE_INTEREST, user_id)

    # Clean up reservation if any
    res_match_id = await redis.get(_reserved_key(user_id))
    if res_match_id:
        if isinstance(res_match_id, bytes):
            res_match_id = res_match_id.decode("utf-8")
        await redis.delete(_reserved_key(user_id))
        await redis.delete(_match_key(res_match_id))
        await redis.delete(_match_accepted_key(res_match_id))

    await redis.delete(_user_req_key(user_id))

    # Mark active DB match request as CANCELLED
    active_req = db.execute(
        select(MatchRequest)
        .where(
            (MatchRequest.user1_id == user_id)
            & (MatchRequest.status.in_(["QUEUED", "MATCH_FOUND"]))
        )
        .order_by(MatchRequest.created_at.desc())
    ).scalars().first()
    if active_req:
        active_req.status = "CANCELLED"
        active_req.completed_at = datetime.now(timezone.utc)
        db.commit()

    # Revert presence to AVAILABLE
    await set_presence_validated(
        redis, user_id, PresenceStatus.AVAILABLE, allow_backend_only=True
    )

    await publish_to_user(
        redis,
        user_id,
        {"type": "matching.cancelled", "user_id": user_id},
    )

    return True, ""


async def get_match_status(
    redis: Redis,
    db: Session,
    user_id: str,
) -> dict[str, Any]:
    """Retrieve current matching state and pending proposals if any."""
    # Check reserved key
    match_id = await redis.get(_reserved_key(user_id))
    if match_id:
        if isinstance(match_id, bytes):
            match_id = match_id.decode("utf-8")
        raw_match = await redis.hgetall(_match_key(match_id))
        if raw_match:
            match_dict = {
                k.decode("utf-8") if isinstance(k, bytes) else k: (
                    v.decode("utf-8") if isinstance(v, bytes) else v
                )
                for k, v in raw_match.items()
            }
            u1_id = match_dict.get("user1_id")
            u2_id = match_dict.get("user2_id")
            peer_id = u2_id if u1_id == user_id else u1_id

            peer = db.execute(
                select(User).options(
                    joinedload(User.interests),
                    joinedload(User.languages),
                    joinedload(User.skills),
                ).where(User.id == peer_id)
            ).unique().scalar_one_or_none()

            accepted_members = await redis.smembers(_match_accepted_key(match_id))
            acc_set = {
                m.decode("utf-8") if isinstance(m, bytes) else str(m)
                for m in accepted_members
            }

            return {
                "status": match_dict.get("status", "MATCH_FOUND"),
                "match_id": match_id,
                "mode": match_dict.get("mode"),
                "score": float(match_dict.get("score", 0)),
                "expires_at": match_dict.get("expires_at"),
                "self_accepted": user_id in acc_set,
                "peer_accepted": peer_id in acc_set,
                "peer": format_peer_summary(peer) if peer else None,
            }

    # Check queue state
    raw_req = await redis.hgetall(_user_req_key(user_id))
    if raw_req:
        req_dict = {
            k.decode("utf-8") if isinstance(k, bytes) else k: (
                v.decode("utf-8") if isinstance(v, bytes) else v
            )
            for k, v in raw_req.items()
        }
        return {
            "status": req_dict.get("status", "QUEUED"),
            "mode": req_dict.get("mode"),
            "joined_at": float(req_dict.get("joined_at", 0)),
        }

    return {"status": "IDLE"}


# ── Proposal & Acceptance Lifecycle ──────────────────────────────────────────


async def propose_match(
    redis: Redis,
    db: Session,
    user1: User,
    user2: User,
    mode: str,
    score: Optional[float] = None,
) -> str:
    """
    Create a match proposal between two reserved users.

    Persists to PostgreSQL, caches proposal in Redis with TTL,
    and publishes 'matching.found' to both participants.
    """
    match_id = str(uuid.uuid4())
    if score is None:
        score = compute_interest_score(user1, user2) if mode == "interest" else None

    expires_at = datetime.now(timezone.utc) + timedelta(seconds=MATCH_TIMEOUT_SECONDS)
    expires_at_iso = expires_at.isoformat()

    # Reserve both users
    await redis.set(_reserved_key(user1.id), match_id, ex=RESERVATION_TTL_SECONDS)
    await redis.set(_reserved_key(user2.id), match_id, ex=RESERVATION_TTL_SECONDS)
    await set_presence(redis, user1.id, PresenceStatus.MATCHING)
    await set_presence(redis, user2.id, PresenceStatus.MATCHING)

    # Cache proposal
    await redis.hset(
        _match_key(match_id),
        mapping={
            "id": match_id,
            "user1_id": user1.id,
            "user2_id": user2.id,
            "mode": mode,
            "status": "MATCH_FOUND",
            "score": str(score if score is not None else 0.0),
            "expires_at": expires_at_iso,
        },
    )
    await redis.expire(_match_key(match_id), RESERVATION_TTL_SECONDS)

    # Persist in DB
    db_match = MatchRequest(
        id=match_id,
        user1_id=user1.id,
        user2_id=user2.id,
        mode=mode,
        status="MATCH_FOUND",
        score=score,
        expires_at=expires_at,
    )
    db.add(db_match)
    db.commit()

    # Send event to user1
    await publish_to_user(
        redis,
        user1.id,
        {
            "type": "matching.found",
            "match_id": match_id,
            "mode": mode,
            "score": score,
            "expires_at": expires_at_iso,
            "peer": format_peer_summary(user2),
        },
    )

    # Send event to user2
    await publish_to_user(
        redis,
        user2.id,
        {
            "type": "matching.found",
            "match_id": match_id,
            "mode": mode,
            "score": score,
            "expires_at": expires_at_iso,
            "peer": format_peer_summary(user1),
        },
    )

    logger.info("Match proposal created: %s between %s and %s (mode=%s)", match_id, user1.id, user2.id, mode)
    return match_id


async def accept_match(
    redis: Redis,
    db: Session,
    user_id: str,
    match_id: str,
) -> tuple[bool, str, dict[str, Any]]:
    """Record acceptance from user_id. If both accept, complete the match."""
    raw_match = await redis.hgetall(_match_key(match_id))
    if not raw_match:
        # Check database
        db_match = db.execute(select(MatchRequest).where(MatchRequest.id == match_id)).scalar_one_or_none()
        if not db_match:
            return False, "Match proposal not found.", {}
        if db_match.status != "MATCH_FOUND":
            return False, f"Match proposal is no longer active (status: {db_match.status}).", {}
        u1_id = db_match.user1_id
        u2_id = db_match.user2_id
    else:
        match_dict = {
            k.decode("utf-8") if isinstance(k, bytes) else k: (
                v.decode("utf-8") if isinstance(v, bytes) else v
            )
            for k, v in raw_match.items()
        }
        u1_id = match_dict.get("user1_id")
        u2_id = match_dict.get("user2_id")

    if user_id not in (u1_id, u2_id):
        return False, "You are not a participant in this match.", {}

    peer_id = u2_id if user_id == u1_id else u1_id

    # Record acceptance in Redis set
    await redis.sadd(_match_accepted_key(match_id), user_id)
    await redis.expire(_match_accepted_key(match_id), RESERVATION_TTL_SECONDS)

    accepted_members = await redis.smembers(_match_accepted_key(match_id))
    acc_set = {
        m.decode("utf-8") if isinstance(m, bytes) else str(m)
        for m in accepted_members
    }

    # Notify users about single acceptance
    await publish_to_user(
        redis,
        user_id,
        {"type": "matching.accepted", "match_id": match_id, "user_id": user_id},
    )
    if peer_id:
        await publish_to_user(
            redis,
            peer_id,
            {"type": "matching.peer_accepted", "match_id": match_id, "user_id": user_id},
        )

    # If both users have accepted: COMPLETE MATCH
    if u1_id in acc_set and u2_id in acc_set:
        now = datetime.now(timezone.utc)
        db_match = db.execute(select(MatchRequest).where(MatchRequest.id == match_id)).scalar_one_or_none()
        if db_match:
            db_match.status = "COMPLETED"
            db_match.user1_accepted = True
            db_match.user2_accepted = True
            db_match.completed_at = now

        # Create or fetch conversation
        conv = db.execute(
            select(Conversation).where(
                or_(
                    (Conversation.participant_a == u1_id) & (Conversation.participant_b == u2_id),
                    (Conversation.participant_a == u2_id) & (Conversation.participant_b == u1_id),
                )
            )
        ).scalar_one_or_none()

        if not conv:
            conv = Conversation(
                id=str(uuid.uuid4()),
                participant_a=u1_id,
                participant_b=u2_id,
                status="active",
            )
            db.add(conv)

        db.commit()

        # Update presences to IN_CONVERSATION
        await set_presence_validated(redis, u1_id, PresenceStatus.IN_CONVERSATION, allow_backend_only=True)
        await set_presence_validated(redis, u2_id, PresenceStatus.IN_CONVERSATION, allow_backend_only=True)

        # Release reservations and matching keys
        await redis.delete(_reserved_key(u1_id))
        await redis.delete(_reserved_key(u2_id))
        await redis.delete(_user_req_key(u1_id))
        await redis.delete(_user_req_key(u2_id))
        await redis.delete(_match_key(match_id))
        await redis.delete(_match_accepted_key(match_id))

        # Publish completion to both participants
        u1_user = db.execute(select(User).where(User.id == u1_id)).scalar_one_or_none()
        u2_user = db.execute(select(User).where(User.id == u2_id)).scalar_one_or_none()

        await publish_to_user(
            redis,
            u1_id,
            {
                "type": "matching.completed",
                "match_id": match_id,
                "conversation_id": conv.id,
                "peer": format_peer_summary(u2_user) if u2_user else None,
            },
        )
        await publish_to_user(
            redis,
            u2_id,
            {
                "type": "matching.completed",
                "match_id": match_id,
                "conversation_id": conv.id,
                "peer": format_peer_summary(u1_user) if u1_user else None,
            },
        )

        return True, "", {
            "status": "COMPLETED",
            "conversation_id": conv.id,
        }

    return True, "", {
        "status": "ACCEPTED",
        "awaiting_peer": True,
    }


async def reject_match(
    redis: Redis,
    db: Session,
    user_id: str,
    match_id: str,
) -> tuple[bool, str]:
    """Decline a match proposal. Reverts participants to AVAILABLE and cleans keys."""
    raw_match = await redis.hgetall(_match_key(match_id))
    u1_id = None
    u2_id = None

    if raw_match:
        match_dict = {
            k.decode("utf-8") if isinstance(k, bytes) else k: (
                v.decode("utf-8") if isinstance(v, bytes) else v
            )
            for k, v in raw_match.items()
        }
        u1_id = match_dict.get("user1_id")
        u2_id = match_dict.get("user2_id")

    db_match = db.execute(select(MatchRequest).where(MatchRequest.id == match_id)).scalar_one_or_none()
    if db_match:
        u1_id = u1_id or db_match.user1_id
        u2_id = u2_id or db_match.user2_id
        db_match.status = "REJECTED"
        if user_id == u1_id:
            db_match.user1_accepted = False
        else:
            db_match.user2_accepted = False
        db_match.completed_at = datetime.now(timezone.utc)
        db.commit()

    if not u1_id or not u2_id:
        return False, "Match not found."

    peer_id = u2_id if user_id == u1_id else u1_id

    # Clean reservations
    await redis.delete(_reserved_key(u1_id))
    await redis.delete(_reserved_key(u2_id))
    await redis.delete(_user_req_key(u1_id))
    await redis.delete(_user_req_key(u2_id))
    await redis.delete(_match_key(match_id))
    await redis.delete(_match_accepted_key(match_id))

    # Revert presences to AVAILABLE
    from app.services.presence_service import set_presence
    await set_presence(redis, u1_id, PresenceStatus.AVAILABLE)
    await set_presence(redis, u2_id, PresenceStatus.AVAILABLE)

    # Notify both
    await publish_to_user(
        redis,
        user_id,
        {"type": "matching.rejected", "match_id": match_id, "by": user_id},
    )
    await publish_to_user(
        redis,
        peer_id,
        {"type": "matching.rejected", "match_id": match_id, "by": user_id},
    )

    return True, ""


async def expire_match(
    redis: Redis,
    db: Session,
    match_id: str,
) -> None:
    """Invoked when the 30-second proposal window expires without mutual acceptance."""
    raw_match = await redis.hgetall(_match_key(match_id))
    u1_id = None
    u2_id = None

    if raw_match:
        match_dict = {
            k.decode("utf-8") if isinstance(k, bytes) else k: (
                v.decode("utf-8") if isinstance(v, bytes) else v
            )
            for k, v in raw_match.items()
        }
        u1_id = match_dict.get("user1_id")
        u2_id = match_dict.get("user2_id")

    db_match = db.execute(select(MatchRequest).where(MatchRequest.id == match_id)).scalar_one_or_none()
    if db_match:
        u1_id = u1_id or db_match.user1_id
        u2_id = u2_id or db_match.user2_id
        db_match.status = "EXPIRED"
        db_match.completed_at = datetime.now(timezone.utc)
        db.commit()

    from app.services.presence_service import set_presence
    if u1_id:
        await redis.delete(_reserved_key(u1_id))
        await redis.delete(_user_req_key(u1_id))
        await set_presence(redis, u1_id, PresenceStatus.AVAILABLE)
        await publish_to_user(redis, u1_id, {"type": "matching.expired", "match_id": match_id})

    if u2_id:
        await redis.delete(_reserved_key(u2_id))
        await redis.delete(_user_req_key(u2_id))
        await set_presence(redis, u2_id, PresenceStatus.AVAILABLE)
        await publish_to_user(redis, u2_id, {"type": "matching.expired", "match_id": match_id})

    await redis.delete(_match_key(match_id))
    await redis.delete(_match_accepted_key(match_id))
    logger.info("Match proposal %s expired.", match_id)
