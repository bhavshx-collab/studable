"""
Studable API — Matching Engine Background Worker (Phase 5).

Runs continuously in the background to:
1. Pair users in Random and Interest-Based matching queues.
2. Prevent concurrency conflicts using distributed Redis locks.
3. Automatically expire proposals exceeding the 30-second acceptance window.
4. Clean up stale queue entries from disconnected users.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.database import SessionLocal
from app.models.match_request import MatchRequest
from app.models.user import User
from app.services.matching_service import (
    QUEUE_INTEREST,
    QUEUE_RANDOM,
    compute_interest_score,
    expire_match,
    is_eligible_pair,
    propose_match,
)
from app.services.presence_service import PresenceStatus, get_presence

logger = logging.getLogger(__name__)

WORKER_LOCK_KEY = "matching:worker:lock"
WORKER_LOCK_TTL = 4


async def run_matching_cycle(redis: Redis, db: Session) -> int:
    """
    Execute one matching evaluation cycle.

    Returns the number of matches formed.
    """
    matches_formed = 0

    # ── 1. Process Random Queue (FIFO) ────────────────────────────────────────
    try:
        random_members = await redis.zrange(QUEUE_RANDOM, 0, -1)
        if len(random_members) >= 2:
            uids = [
                m.decode("utf-8") if isinstance(m, bytes) else str(m)
                for m in random_members
            ]

            users = db.execute(
                select(User).options(
                    joinedload(User.interests),
                    joinedload(User.languages),
                    joinedload(User.skills),
                    joinedload(User.sent_connections),
                    joinedload(User.received_connections),
                ).where(User.id.in_(uids))
            ).unique().scalars().all()
            user_map = {u.id: u for u in users}

            i = 0
            while i < len(uids) - 1:
                u1_id = uids[i]
                u1 = user_map.get(u1_id)
                if not u1:
                    await redis.zrem(QUEUE_RANDOM, u1_id)
                    i += 1
                    continue

                # Verify user1 is still MATCHING / active
                p1 = await get_presence(redis, u1_id)
                if p1 not in (PresenceStatus.MATCHING, PresenceStatus.AVAILABLE):
                    await redis.zrem(QUEUE_RANDOM, u1_id)
                    i += 1
                    continue

                matched = False
                for j in range(i + 1, len(uids)):
                    u2_id = uids[j]
                    u2 = user_map.get(u2_id)
                    if not u2:
                        continue

                    p2 = await get_presence(redis, u2_id)
                    if p2 not in (PresenceStatus.MATCHING, PresenceStatus.AVAILABLE):
                        await redis.zrem(QUEUE_RANDOM, u2_id)
                        continue

                    if is_eligible_pair(db, u1, u2, mode="random"):
                        # Atomically remove both from queue
                        await redis.zrem(QUEUE_RANDOM, u1_id, u2_id)
                        await propose_match(redis, db, u1, u2, mode="random")
                        matches_formed += 1
                        matched = True
                        uids.pop(j)
                        break

                i += 1
    except Exception as exc:
        logger.error("Error processing random matching queue: %s", exc)

    # ── 2. Process Interest-Based Queue ───────────────────────────────────────
    try:
        interest_members = await redis.zrange(QUEUE_INTEREST, 0, -1, withscores=True)
        if len(interest_members) >= 2:
            uid_scores = [
                (
                    m[0].decode("utf-8") if isinstance(m[0], bytes) else str(m[0]),
                    float(m[1]),
                )
                for m in interest_members
            ]
            uids = [item[0] for item in uid_scores]

            users = db.execute(
                select(User).options(
                    joinedload(User.interests),
                    joinedload(User.languages),
                    joinedload(User.skills),
                    joinedload(User.sent_connections),
                    joinedload(User.received_connections),
                ).where(User.id.in_(uids))
            ).unique().scalars().all()
            user_map = {u.id: u for u in users}

            now_ts = time.time()
            evaluated_pairs: list[tuple[float, User, User]] = []

            for i in range(len(uids)):
                for j in range(i + 1, len(uids)):
                    u1_id, t1 = uid_scores[i]
                    u2_id, t2 = uid_scores[j]
                    u1 = user_map.get(u1_id)
                    u2 = user_map.get(u2_id)
                    if not u1 or not u2:
                        continue

                    if is_eligible_pair(db, u1, u2, mode="interest"):
                        base_score = compute_interest_score(u1, u2)
                        # Wait time bonus: +1 point per 10s waiting (max 20 points)
                        wait_bonus = min(20.0, ((now_ts - min(t1, t2)) / 10.0))
                        total_score = min(100.0, base_score + wait_bonus)
                        evaluated_pairs.append((total_score, u1, u2))

            # Sort descending by score
            evaluated_pairs.sort(key=lambda x: x[0], reverse=True)

            matched_uids: set[str] = set()
            for score, u1, u2 in evaluated_pairs:
                if u1.id in matched_uids or u2.id in matched_uids:
                    continue

                p1 = await get_presence(redis, u1.id)
                p2 = await get_presence(redis, u2.id)
                if p1 not in (PresenceStatus.MATCHING, PresenceStatus.AVAILABLE):
                    await redis.zrem(QUEUE_INTEREST, u1.id)
                    continue
                if p2 not in (PresenceStatus.MATCHING, PresenceStatus.AVAILABLE):
                    await redis.zrem(QUEUE_INTEREST, u2.id)
                    continue

                # Form match
                await redis.zrem(QUEUE_INTEREST, u1.id, u2.id)
                await propose_match(redis, db, u1, u2, mode="interest", score=score)
                matched_uids.add(u1.id)
                matched_uids.add(u2.id)
                matches_formed += 1
    except Exception as exc:
        logger.error("Error processing interest matching queue: %s", exc)

    # ── 3. Expire Stale Proposals (30-second window) ──────────────────────────
    try:
        now_dt = datetime.now(timezone.utc)
        expired_proposals = db.execute(
            select(MatchRequest).where(
                (MatchRequest.status == "MATCH_FOUND")
                & (MatchRequest.expires_at <= now_dt)
            )
        ).scalars().all()

        for prop in expired_proposals:
            await expire_match(redis, db, prop.id)
    except Exception as exc:
        logger.error("Error expiring match proposals: %s", exc)

    return matches_formed


async def matching_worker_loop(redis: Redis, interval: float = 2.0) -> None:
    """Infinite background loop running match formation with distributed locking."""
    logger.info("Matching background worker started (interval=%.1fs)", interval)
    while True:
        try:
            # Distributed lock: only one worker evaluates matching queues across processes
            acquired = await redis.set(WORKER_LOCK_KEY, "locked", nx=True, ex=WORKER_LOCK_TTL)
            if acquired:
                try:
                    db = SessionLocal()
                    try:
                        await run_matching_cycle(redis, db)
                    finally:
                        db.close()
                finally:
                    # Release lock early if still matching
                    await redis.delete(WORKER_LOCK_KEY)
        except asyncio.CancelledError:
            logger.info("Matching background worker stopping...")
            break
        except Exception as exc:
            logger.warning("Matching worker loop exception: %s", exc)

        await asyncio.sleep(interval)
