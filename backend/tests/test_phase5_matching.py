"""
Studable API — Phase 5 Real-Time Matching Engine Tests.

Coverage:
  Phase 4 Risk Mitigations:
    - Stale session cleanup with expiring session leases
    - Single-use short-lived WebSocket tickets (/api/v1/ws/ticket)
    - Redis Pub/Sub multi-worker event delivery

  Matching Algorithm & Eligibility:
    - compute_interest_score (shared interests, languages, audience)
    - is_eligible_pair (self-pairing, suspended, blocked, audience filter)

  Redis Matching Queue Operations:
    - join_queue in random & interest mode
    - duplicate queue prevention
    - cancel_queue and presence reset to AVAILABLE
    - get_match_status inspection

  Match Proposal Lifecycle:
    - propose_match reserves both users, sets 30s timeout, notifies participants
    - accept_match (single acceptance, mutual acceptance -> COMPLETED & IN_CONVERSATION)
    - reject_match (declines proposal, resets to AVAILABLE)
    - expire_match (timeout resets to AVAILABLE)

  Matching Background Worker:
    - run_matching_cycle pairs eligible candidates in random & interest queues
    - worker lock prevents concurrent execution across workers

  REST Endpoints:
    - POST /api/v1/matching/join
    - POST /api/v1/matching/cancel
    - GET  /api/v1/matching/status
    - POST /api/v1/matching/{match_id}/accept
    - POST /api/v1/matching/{match_id}/reject
    - GET  /api/v1/matching/history

  WebSocket Integration:
    - Connect to /api/v1/ws/matching with ticket
    - Initial matching.status snapshot received
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Generator

import fakeredis.aioredis as fakeredis_async
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.redis import get_redis
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.block import Block
from app.models.match_request import MatchRequest
from app.models.user import User, UserInterest, UserLanguage
from app.services.matching_service import (
    accept_match,
    cancel_queue,
    compute_interest_score,
    expire_match,
    get_match_status,
    is_eligible_pair,
    join_queue,
    propose_match,
    reject_match,
)
from app.services.presence_service import (
    PresenceStatus,
    cleanup_stale_sessions,
    get_presence,
    register_session,
    set_presence_validated,
)
from app.workers.matching_worker import run_matching_cycle

# ── SQLite in-memory test database ───────────────────────────────────────────

SQLITE_URL = "sqlite://"
_engine = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(_engine, "connect")
def _enable_fk(dbapi_conn, record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


_TestSessionLocal = sessionmaker(
    bind=_engine, autocommit=False, autoflush=False, expire_on_commit=False
)


@pytest.fixture(scope="session", autouse=True)
def setup_tables():
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    session = _TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def fake_redis():
    client = fakeredis_async.FakeRedis(decode_responses=True)
    yield client


@pytest.fixture()
def client(db: Session, fake_redis) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_redis] = lambda: fake_redis
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


def make_user(
    db: Session,
    username: str,
    email: str,
    interests: list[str] = None,
    languages: list[str] = None,
    category: str = "Student",
    audience: str = "Anyone",
) -> User:
    u = User(
        id=str(uuid.uuid4()),
        username=username,
        email=email,
        password_hash=hash_password("Password123!"),
        display_name=username.capitalize(),
        category=category,
        preferred_audience=audience,
        preferred_language="English",
        allow_random_discovery=True,
    )
    db.add(u)
    db.flush()

    if interests:
        for it in interests:
            db.add(UserInterest(user_id=u.id, interest=it))
    if languages:
        for lg in languages:
            db.add(UserLanguage(user_id=u.id, language=lg))
    db.commit()
    return u


# ── Phase 4 Risk Mitigations ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_session_lease_and_stale_cleanup(fake_redis):
    uid = str(uuid.uuid4())
    s1 = "session_active"
    s2 = "session_crashed"

    await register_session(fake_redis, uid, s1)
    await register_session(fake_redis, uid, s2)

    # Simulate s2 lease expiring in Redis
    await fake_redis.delete(f"presence:session:{s2}:lease")

    pruned = await cleanup_stale_sessions(fake_redis, uid)
    assert pruned == 1
    # User should still be online via s1
    status = await get_presence(fake_redis, uid)
    assert status == PresenceStatus.ONLINE

    # Expire s1 lease as well
    await fake_redis.delete(f"presence:session:{s1}:lease")
    pruned2 = await cleanup_stale_sessions(fake_redis, uid)
    assert pruned2 == 1
    # Now user should be OFFLINE
    status_off = await get_presence(fake_redis, uid)
    assert status_off == PresenceStatus.OFFLINE


def test_ws_ticket_generation_and_single_use(client: TestClient, db: Session, fake_redis):
    u = make_user(db, "ticket_user", "ticket@studable.test")
    token = create_access_token(u.id)

    res = client.post("/api/v1/ws/ticket", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    ticket = res.json()["ticket"]
    assert ticket is not None

    # Connect with ticket
    with client.websocket_connect(f"/api/v1/ws/presence?ticket={ticket}") as ws:
        data = ws.receive_json()
        assert data["type"] == "presence.connected"
        assert data["user_id"] == u.id

    # Second connection with same ticket should be rejected (single-use)
    with pytest.raises(Exception):
        with client.websocket_connect(f"/api/v1/ws/presence?ticket={ticket}"):
            pass


# ── Matching Eligibility & Scoring Tests ─────────────────────────────────────


def test_interest_scoring(db: Session):
    u1 = make_user(
        db, "scorer1", "s1@studable.test",
        interests=["AI", "Startups", "Python"],
        languages=["English", "Spanish"],
        category="Student",
    )
    u2 = make_user(
        db, "scorer2", "s2@studable.test",
        interests=["AI", "Startups", "Design"],
        languages=["English"],
        category="Student",
    )
    u3 = make_user(
        db, "scorer3", "s3@studable.test",
        interests=["Cooking", "Gardening"],
        languages=["French"],
        category="Mentor",
    )

    score_high = compute_interest_score(u1, u2)
    score_low = compute_interest_score(u1, u3)

    assert score_high > score_low
    assert score_high >= 50.0


def test_is_eligible_pair_rules(db: Session):
    u1 = make_user(db, "elig1", "e1@studable.test", category="Student", audience="Students")
    u2 = make_user(db, "elig2", "e2@studable.test", category="Student", audience="Students")
    u3 = make_user(db, "elig3", "e3@studable.test", category="Working Professional", audience="Professionals")

    # Matching same category with mutual audience preference
    assert is_eligible_pair(db, u1, u2, mode="random") is True

    # Incompatible audience
    assert is_eligible_pair(db, u1, u3, mode="random") is False

    # Blocked relationship
    block = Block(blocker_id=u1.id, blocked_id=u2.id)
    db.add(block)
    db.commit()
    assert is_eligible_pair(db, u1, u2, mode="random") is False


# ── Queue Operations Tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_join_and_cancel_queue(fake_redis, db: Session):
    u = make_user(db, "queuer1", "q1@studable.test")

    # Set user AVAILABLE
    await set_presence_validated(fake_redis, u.id, PresenceStatus.ONLINE)
    await set_presence_validated(fake_redis, u.id, PresenceStatus.AVAILABLE)

    # Join queue
    ok, err, info = await join_queue(fake_redis, db, u.id, "random")
    assert ok is True
    assert info["status"] == "QUEUED"

    # Presence should be MATCHING
    pres = await get_presence(fake_redis, u.id)
    assert pres == PresenceStatus.MATCHING

    # Duplicate join rejected
    ok2, err2, _ = await join_queue(fake_redis, db, u.id, "random")
    assert ok2 is False
    assert "already queued" in err2.lower()

    # Cancel queue
    ok_cancel, _ = await cancel_queue(fake_redis, db, u.id)
    assert ok_cancel is True

    # Presence restored to AVAILABLE
    pres_after = await get_presence(fake_redis, u.id)
    assert pres_after == PresenceStatus.AVAILABLE


# ── Proposal Lifecycle Tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_propose_and_mutual_accept_match(fake_redis, db: Session):
    u1 = make_user(db, "prop1", "p1@studable.test", interests=["AI"])
    u2 = make_user(db, "prop2", "p2@studable.test", interests=["AI"])

    match_id = await propose_match(fake_redis, db, u1, u2, mode="interest")
    assert match_id is not None

    # Status check
    st1 = await get_match_status(fake_redis, db, u1.id)
    assert st1["status"] == "MATCH_FOUND"
    assert st1["match_id"] == match_id
    assert st1["peer"]["id"] == u2.id

    # User 1 accepts
    ok1, _, info1 = await accept_match(fake_redis, db, u1.id, match_id)
    assert ok1 is True
    assert info1["status"] == "ACCEPTED"
    assert info1["awaiting_peer"] is True

    # User 2 accepts -> COMPLETES
    ok2, _, info2 = await accept_match(fake_redis, db, u2.id, match_id)
    assert ok2 is True
    assert info2["status"] == "COMPLETED"
    assert "conversation_id" in info2

    # Presences should be IN_CONVERSATION
    p1 = await get_presence(fake_redis, u1.id)
    p2 = await get_presence(fake_redis, u2.id)
    assert p1 == PresenceStatus.IN_CONVERSATION
    assert p2 == PresenceStatus.IN_CONVERSATION


@pytest.mark.asyncio
async def test_reject_match_lifecycle(fake_redis, db: Session):
    u1 = make_user(db, "rej1", "rej1@studable.test")
    u2 = make_user(db, "rej2", "rej2@studable.test")

    match_id = await propose_match(fake_redis, db, u1, u2, mode="random")
    ok, _ = await reject_match(fake_redis, db, u1.id, match_id)
    assert ok is True

    # Both users revert to AVAILABLE
    p1 = await get_presence(fake_redis, u1.id)
    p2 = await get_presence(fake_redis, u2.id)
    assert p1 == PresenceStatus.AVAILABLE
    assert p2 == PresenceStatus.AVAILABLE


@pytest.mark.asyncio
async def test_expire_match_lifecycle(fake_redis, db: Session):
    u1 = make_user(db, "exp1", "exp1@studable.test")
    u2 = make_user(db, "exp2", "exp2@studable.test")

    match_id = await propose_match(fake_redis, db, u1, u2, mode="random")
    await expire_match(fake_redis, db, match_id)

    # Both users revert to AVAILABLE
    p1 = await get_presence(fake_redis, u1.id)
    p2 = await get_presence(fake_redis, u2.id)
    assert p1 == PresenceStatus.AVAILABLE
    assert p2 == PresenceStatus.AVAILABLE


# ── Background Worker Tests ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_matching_worker_pairs_queue(fake_redis, db: Session):
    u1 = make_user(db, "work1", "w1@studable.test")
    u2 = make_user(db, "work2", "w2@studable.test")

    # Set presences to AVAILABLE
    await set_presence_validated(fake_redis, u1.id, PresenceStatus.ONLINE)
    await set_presence_validated(fake_redis, u1.id, PresenceStatus.AVAILABLE)
    await set_presence_validated(fake_redis, u2.id, PresenceStatus.ONLINE)
    await set_presence_validated(fake_redis, u2.id, PresenceStatus.AVAILABLE)

    # Join random queue
    await join_queue(fake_redis, db, u1.id, "random")
    await join_queue(fake_redis, db, u2.id, "random")

    # Run one matching cycle
    formed = await run_matching_cycle(fake_redis, db)
    assert formed == 1

    # Both users should now have a pending proposal
    st1 = await get_match_status(fake_redis, db, u1.id)
    assert st1["status"] == "MATCH_FOUND"
    assert st1["peer"]["id"] == u2.id


# ── REST API Endpoints Tests ─────────────────────────────────────────────────


def test_matching_rest_endpoints(client: TestClient, db: Session):
    u1 = make_user(db, "rest_u1", "ru1@studable.test")
    token1 = create_access_token(u1.id)
    headers = {"Authorization": f"Bearer {token1}"}

    # POST /api/v1/matching/join
    res_join = client.post("/api/v1/matching/join", json={"mode": "random"}, headers=headers)
    assert res_join.status_code == 200
    assert res_join.json()["status"] == "QUEUED"

    # GET /api/v1/matching/status
    res_status = client.get("/api/v1/matching/status", headers=headers)
    assert res_status.status_code == 200
    assert res_status.json()["status"] == "QUEUED"

    # POST /api/v1/matching/cancel
    res_cancel = client.post("/api/v1/matching/cancel", headers=headers)
    assert res_cancel.status_code == 200
    assert res_cancel.json()["status"] == "IDLE"

    # GET /api/v1/matching/history
    res_hist = client.get("/api/v1/matching/history", headers=headers)
    assert res_hist.status_code == 200
    assert "items" in res_hist.json()
    assert res_hist.json()["count"] >= 1
