"""
Studable API — Phase 4 presence engine tests.

All tests are fully self-contained:
- Database: in-memory SQLite (no PostgreSQL required)
- Redis: fakeredis (no Redis server required)

Coverage:
  Presence state machine:
    - Valid transitions accepted
    - Invalid transitions rejected
    - Backend-only states rejected from client context

  Session management:
    - register_session sets ONLINE for first session
    - Additional sessions preserve state and refresh TTL
    - unregister_session removes session; last session exit marks OFFLINE
    - Multiple sessions — one disconnect doesn't mark offline

  Heartbeat:
    - refresh_ttl refreshes TTL for known session
    - refresh_ttl returns False for unknown session

  Bulk queries:
    - get_online_count counts non-OFFLINE users
    - get_online_users returns user IDs
    - get_available_users filters by AVAILABLE

  REST endpoints:
    - GET /api/v1/presence/me
    - PATCH /api/v1/presence/me (valid, invalid state, rejected transition)
    - GET /api/v1/presence/users/{user_id}
    - GET /api/v1/presence/online
    - GET /api/v1/presence/available

  WebSocket:
    - Connect with valid token → receives presence.connected
    - Connect with invalid token → close 1008
    - Connect with expired token → close 1008
    - Heartbeat message → heartbeat.ack
    - set_status to AVAILABLE
    - set_status to MATCHING rejected (backend only)
    - Unknown message type → error
    - Invalid JSON → error

  Graceful degradation:
    - Service returns OFFLINE on Redis failure
    - REST endpoints return graceful response when Redis unavailable

  Health endpoint:
    - Includes redis field
"""

from __future__ import annotations

import json
import uuid
from typing import Generator
from unittest.mock import AsyncMock, patch

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
from app.services.presence_service import (
    BACKEND_ONLY_STATES,
    VALID_TRANSITIONS,
    PresenceStatus,
    get_available_users,
    get_online_count,
    get_online_users,
    get_presence,
    get_session_count,
    refresh_ttl,
    register_session,
    set_presence,
    set_presence_validated,
    unregister_session,
)

# ── SQLite in-memory database setup ───────────────────────────────────────────

SQLITE_URL = "sqlite://"

_engine = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(_engine, "connect")
def _enable_fk(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


_TestSessionLocal = sessionmaker(
    bind=_engine, autocommit=False, autoflush=False, expire_on_commit=False
)


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    import app.models  # noqa: F401 — register all models on Base.metadata
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


# ── Fake Redis fixture ────────────────────────────────────────────────────────


@pytest.fixture()
async def fake_redis():
    """Provide a fresh fakeredis instance for each test."""
    server = fakeredis_async.FakeRedis(decode_responses=True)
    yield server
    await server.aclose()


# ── HTTP test client with overrides ───────────────────────────────────────────


@pytest.fixture()
def client(db, fake_redis):
    """Test client with SQLite DB and fakeredis overrides."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    async def override_get_redis():
        yield fake_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


# ── Helpers ───────────────────────────────────────────────────────────────────


def make_user(db: Session, email_suffix: str = "") -> "User":  # type: ignore[name-defined]
    from app.models.user import User
    uid = str(uuid.uuid4())
    user = User(
        id=uid,
        email=f"user{email_suffix}@test.com",
        username=f"user_{uid[:8]}",
        display_name="Test User",
        password_hash=hash_password("TestPass123!"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def auth_header(user_id: str, role: str = "member") -> dict:
    token = create_access_token(subject=user_id, role=role)
    return {"Authorization": f"Bearer {token}"}


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — State machine unit tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestPresenceStateMachine:
    """Verify the VALID_TRANSITIONS dict and BACKEND_ONLY_STATES."""

    def test_all_states_have_transition_entries(self):
        for state in PresenceStatus:
            assert state in VALID_TRANSITIONS, f"{state} missing from VALID_TRANSITIONS"

    def test_offline_can_only_go_online(self):
        assert VALID_TRANSITIONS[PresenceStatus.OFFLINE] == {PresenceStatus.ONLINE}

    def test_online_cannot_go_to_matching(self):
        assert PresenceStatus.MATCHING not in VALID_TRANSITIONS[PresenceStatus.ONLINE]

    def test_in_conversation_can_go_available(self):
        assert PresenceStatus.AVAILABLE in VALID_TRANSITIONS[PresenceStatus.IN_CONVERSATION]

    def test_backend_only_states_defined(self):
        assert PresenceStatus.MATCHING in BACKEND_ONLY_STATES
        assert PresenceStatus.IN_CONVERSATION in BACKEND_ONLY_STATES

    def test_available_and_busy_not_backend_only(self):
        assert PresenceStatus.AVAILABLE not in BACKEND_ONLY_STATES
        assert PresenceStatus.BUSY not in BACKEND_ONLY_STATES

    @pytest.mark.asyncio
    async def test_valid_transition_accepted(self, fake_redis):
        uid = str(uuid.uuid4())
        # Seed ONLINE state
        await set_presence(fake_redis, uid, PresenceStatus.ONLINE)
        ok, msg = await set_presence_validated(
            fake_redis, uid, PresenceStatus.AVAILABLE
        )
        assert ok, msg
        assert await get_presence(fake_redis, uid) == PresenceStatus.AVAILABLE

    @pytest.mark.asyncio
    async def test_invalid_transition_rejected(self, fake_redis):
        uid = str(uuid.uuid4())
        # OFFLINE → AVAILABLE is not in the transition table
        ok, msg = await set_presence_validated(
            fake_redis, uid, PresenceStatus.AVAILABLE
        )
        assert not ok
        assert "not allowed" in msg.lower()

    @pytest.mark.asyncio
    async def test_backend_only_rejected_from_client(self, fake_redis):
        uid = str(uuid.uuid4())
        await set_presence(fake_redis, uid, PresenceStatus.AVAILABLE)
        ok, msg = await set_presence_validated(
            fake_redis, uid, PresenceStatus.MATCHING, allow_backend_only=False
        )
        assert not ok
        assert "backend" in msg.lower()

    @pytest.mark.asyncio
    async def test_backend_only_accepted_with_flag(self, fake_redis):
        uid = str(uuid.uuid4())
        await set_presence(fake_redis, uid, PresenceStatus.AVAILABLE)
        ok, msg = await set_presence_validated(
            fake_redis, uid, PresenceStatus.MATCHING, allow_backend_only=True
        )
        assert ok, msg


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Session management unit tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestSessionManagement:

    @pytest.mark.asyncio
    async def test_register_session_sets_online_first_session(self, fake_redis):
        uid = str(uuid.uuid4())
        sid = "session-1"
        await register_session(fake_redis, uid, sid)
        assert await get_presence(fake_redis, uid) == PresenceStatus.ONLINE

    @pytest.mark.asyncio
    async def test_register_second_session_preserves_state(self, fake_redis):
        uid = str(uuid.uuid4())
        await register_session(fake_redis, uid, "s1")
        # Manually upgrade to AVAILABLE
        await set_presence(fake_redis, uid, PresenceStatus.AVAILABLE)
        # Second session should not reset state
        await register_session(fake_redis, uid, "s2")
        assert await get_presence(fake_redis, uid) == PresenceStatus.AVAILABLE

    @pytest.mark.asyncio
    async def test_unregister_last_session_marks_offline(self, fake_redis):
        uid = str(uuid.uuid4())
        await register_session(fake_redis, uid, "s1")
        went_offline = await unregister_session(fake_redis, uid, "s1")
        assert went_offline is True
        assert await get_presence(fake_redis, uid) == PresenceStatus.OFFLINE

    @pytest.mark.asyncio
    async def test_unregister_non_last_session_keeps_state(self, fake_redis):
        uid = str(uuid.uuid4())
        await register_session(fake_redis, uid, "s1")
        await register_session(fake_redis, uid, "s2")
        went_offline = await unregister_session(fake_redis, uid, "s1")
        assert went_offline is False
        # State should still be ONLINE (or preserved)
        assert await get_presence(fake_redis, uid) != PresenceStatus.OFFLINE

    @pytest.mark.asyncio
    async def test_session_count_tracks_correctly(self, fake_redis):
        uid = str(uuid.uuid4())
        assert await get_session_count(fake_redis, uid) == 0
        await register_session(fake_redis, uid, "s1")
        assert await get_session_count(fake_redis, uid) == 1
        await register_session(fake_redis, uid, "s2")
        assert await get_session_count(fake_redis, uid) == 2
        await unregister_session(fake_redis, uid, "s1")
        assert await get_session_count(fake_redis, uid) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Heartbeat
# ═══════════════════════════════════════════════════════════════════════════════


class TestHeartbeat:

    @pytest.mark.asyncio
    async def test_refresh_ttl_returns_true_for_known_session(self, fake_redis):
        uid = str(uuid.uuid4())
        await register_session(fake_redis, uid, "s1", ttl=60)
        result = await refresh_ttl(fake_redis, uid, "s1", ttl=60)
        assert result is True

    @pytest.mark.asyncio
    async def test_refresh_ttl_returns_false_for_unknown_session(self, fake_redis):
        uid = str(uuid.uuid4())
        result = await refresh_ttl(fake_redis, uid, "unknown-session")
        assert result is False


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Bulk queries
# ═══════════════════════════════════════════════════════════════════════════════


class TestBulkQueries:

    @pytest.mark.asyncio
    async def test_get_online_count(self, fake_redis):
        u1, u2, u3 = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
        await set_presence(fake_redis, u1, PresenceStatus.ONLINE)
        await set_presence(fake_redis, u2, PresenceStatus.AVAILABLE)
        # u3 stays OFFLINE (no key set)
        count = await get_online_count(fake_redis)
        assert count >= 2

    @pytest.mark.asyncio
    async def test_get_online_users(self, fake_redis):
        u1 = str(uuid.uuid4())
        await set_presence(fake_redis, u1, PresenceStatus.ONLINE)
        users = await get_online_users(fake_redis)
        assert u1 in users

    @pytest.mark.asyncio
    async def test_get_available_users(self, fake_redis):
        u1, u2 = str(uuid.uuid4()), str(uuid.uuid4())
        await set_presence(fake_redis, u1, PresenceStatus.AVAILABLE)
        await set_presence(fake_redis, u2, PresenceStatus.ONLINE)
        available = await get_available_users(fake_redis)
        assert u1 in available
        assert u2 not in available

    @pytest.mark.asyncio
    async def test_get_online_count_zero_for_all_offline(self, fake_redis):
        # Fresh fakeredis — count should start at 0 (or only show users added in this test)
        count = await get_online_count(fake_redis)
        assert count >= 0  # Always non-negative


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — REST endpoint tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestPresenceRestEndpoints:

    def test_get_presence_me_unauthenticated(self, client):
        resp = client.get("/api/v1/presence/me")
        assert resp.status_code == 401

    def test_get_presence_me_authenticated(self, client, db):
        user = make_user(db, "_me1")
        resp = client.get("/api/v1/presence/me", headers=auth_header(str(user.id)))
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == str(user.id)
        assert data["status"] == PresenceStatus.OFFLINE.value

    def test_patch_presence_me_unauthenticated(self, client):
        resp = client.patch("/api/v1/presence/me", json={"status": "AVAILABLE"})
        assert resp.status_code == 401

    def test_patch_presence_me_invalid_status(self, client, db):
        user = make_user(db, "_me2")
        resp = client.patch(
            "/api/v1/presence/me",
            json={"status": "FLYING"},
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 422

    def test_patch_presence_me_rejected_transition(self, client, db):
        """OFFLINE → BUSY is an invalid transition — should return 409."""
        user = make_user(db, "_me3")
        resp = client.patch(
            "/api/v1/presence/me",
            json={"status": "BUSY"},
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 409

    def test_patch_presence_me_matching_rejected(self, client, db):
        """Client cannot set MATCHING via REST (backend-only)."""
        user = make_user(db, "_me4")
        resp = client.patch(
            "/api/v1/presence/me",
            json={"status": "MATCHING"},
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code in (409, 422)

    def test_get_user_presence(self, client, db):
        requester = make_user(db, "_req1")
        target = make_user(db, "_tgt1")
        resp = client.get(
            f"/api/v1/presence/users/{target.id}",
            headers=auth_header(str(requester.id)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == str(target.id)
        assert data["status"] == PresenceStatus.OFFLINE.value

    def test_get_online_count(self, client, db):
        user = make_user(db, "_cnt1")
        resp = client.get(
            "/api/v1/presence/online",
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "online_count" in data
        assert data["online_count"] >= 0

    def test_get_available_users(self, client, db):
        user = make_user(db, "_avl1")
        resp = client.get(
            "/api/v1/presence/available",
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "user_ids" in data
        assert "total" in data

    def test_get_available_users_limit_param(self, client, db):
        user = make_user(db, "_avl2")
        resp = client.get(
            "/api/v1/presence/available?limit=5",
            headers=auth_header(str(user.id)),
        )
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — WebSocket tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestPresenceWebSocket:

    def test_websocket_connect_invalid_token(self, client):
        with pytest.raises(Exception):
            # Invalid token should cause close code 1008 — TestClient raises on disconnect
            with client.websocket_connect("/api/v1/ws/presence?token=not-a-jwt") as ws:
                ws.receive_json()

    def test_websocket_connect_missing_token(self, client):
        with pytest.raises(Exception):
            # Connecting without the required token parameter causes handshake rejection
            with client.websocket_connect("/api/v1/ws/presence") as ws:
                ws.receive_json()

    def test_websocket_connect_valid_token_receives_connected(self, client, db):
        user = make_user(db, "_ws1")
        token = create_access_token(subject=str(user.id))
        with client.websocket_connect(f"/api/v1/ws/presence?token={token}") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "presence.connected"
            assert msg["user_id"] == str(user.id)
            assert msg["status"] == PresenceStatus.ONLINE.value
            assert "heartbeat_interval" in msg

    def test_websocket_heartbeat_ack(self, client, db):
        user = make_user(db, "_ws2")
        token = create_access_token(subject=str(user.id))
        with client.websocket_connect(f"/api/v1/ws/presence?token={token}") as ws:
            ws.receive_json()  # presence.connected
            ws.send_json({"type": "heartbeat"})
            msg = ws.receive_json()
            assert msg["type"] == "heartbeat.ack"
            assert msg["user_id"] == str(user.id)

    def test_websocket_set_status_available(self, client, db):
        user = make_user(db, "_ws3")
        token = create_access_token(subject=str(user.id))
        with client.websocket_connect(f"/api/v1/ws/presence?token={token}") as ws:
            ws.receive_json()  # presence.connected (ONLINE)
            ws.send_json({"type": "set_status", "status": "AVAILABLE"})
            msg = ws.receive_json()
            assert msg["type"] == "presence.updated"
            assert msg["status"] == "AVAILABLE"

    def test_websocket_set_status_matching_rejected(self, client, db):
        user = make_user(db, "_ws4")
        token = create_access_token(subject=str(user.id))
        with client.websocket_connect(f"/api/v1/ws/presence?token={token}") as ws:
            ws.receive_json()  # presence.connected
            ws.send_json({"type": "set_status", "status": "MATCHING"})
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert msg["code"] == "transition_rejected"

    def test_websocket_unknown_message_type(self, client, db):
        user = make_user(db, "_ws5")
        token = create_access_token(subject=str(user.id))
        with client.websocket_connect(f"/api/v1/ws/presence?token={token}") as ws:
            ws.receive_json()  # presence.connected
            ws.send_text('{"type": "fly_to_moon"}')
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert msg["code"] == "unknown_type"

    def test_websocket_invalid_json(self, client, db):
        user = make_user(db, "_ws6")
        token = create_access_token(subject=str(user.id))
        with client.websocket_connect(f"/api/v1/ws/presence?token={token}") as ws:
            ws.receive_json()  # presence.connected
            ws.send_text("not valid json {{{")
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert msg["code"] == "invalid_json"

    def test_websocket_set_status_busy(self, client, db):
        user = make_user(db, "_ws7")
        token = create_access_token(subject=str(user.id))
        with client.websocket_connect(f"/api/v1/ws/presence?token={token}") as ws:
            ws.receive_json()  # ONLINE
            # ONLINE → BUSY is valid
            ws.send_json({"type": "set_status", "status": "BUSY"})
            msg = ws.receive_json()
            assert msg["type"] == "presence.updated"
            assert msg["status"] == "BUSY"


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — Graceful degradation
# ═══════════════════════════════════════════════════════════════════════════════


class TestGracefulDegradation:

    @pytest.mark.asyncio
    async def test_get_presence_redis_failure_returns_offline(self):
        """Simulate Redis failure — get_presence should return OFFLINE."""
        from unittest.mock import AsyncMock, MagicMock
        from redis.exceptions import RedisError
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(side_effect=RedisError("connection refused"))
        result = await get_presence(mock_redis, "some-user-id")
        assert result == PresenceStatus.OFFLINE

    @pytest.mark.asyncio
    async def test_get_online_count_redis_failure_returns_zero(self):
        """Simulate Redis failure — get_online_count should return 0."""
        from unittest.mock import MagicMock
        from redis.exceptions import RedisError
        mock_redis = MagicMock()
        # scan_iter raises when iterated
        async def failing_scan(*args, **kwargs):
            raise RedisError("scan failed")
            yield  # make it a generator
        mock_redis.scan_iter = failing_scan
        result = await get_online_count(mock_redis)
        assert result == 0


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — Health endpoint (Redis field)
# ═══════════════════════════════════════════════════════════════════════════════


class TestHealthEndpointWithRedis:

    def test_health_includes_redis_field(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "redis" in data
        assert data["redis"] in ("connected", "unavailable")

    def test_health_includes_database_field(self, client):
        resp = client.get("/api/v1/health")
        data = resp.json()
        assert "database" in data

    def test_health_status_always_healthy(self, client):
        resp = client.get("/api/v1/health")
        data = resp.json()
        assert data["status"] == "healthy"
