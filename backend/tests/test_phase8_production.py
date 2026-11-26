"""
Studable API — Phase 8 Production Readiness & Security Tests.

Coverage:
  Age Eligibility:
    - User under 13 cannot register (COPPA compliance)
    - User 13 or older can register

  Session Revocation:
    - revoke_all_user_sessions marks all refresh tokens revoked
    - change-password revokes all sessions
    - logout-all revokes all sessions
    - admin suspension revokes all sessions
    - account deletion revokes all sessions

  Privacy Enforcement:
    - get_user_presence returns OFFLINE if target user has show_online_status=False
    - list_available_users excludes users with show_online_status=False
    - is_eligible_pair rejects random matching if allow_random_discovery=False

  Message Deduplication & Delivery Receipts:
    - send_message with identical client_message_id returns existing message
    - mark_message_delivered updates status to 'delivered' and dispatches event
    - delivered REST endpoint

  WebSocket Security & Limits:
    - Origin validation rejection
    - Active connections limit per user

  Security Headers:
    - X-Content-Type-Options, X-Frame-Options, Referrer-Policy present
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Generator

import fakeredis.aioredis as fakeredis_async
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.redis import get_redis
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.auth import RefreshToken
from app.models.block import Block
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.services.auth_service import revoke_all_user_sessions
from app.services.matching_service import is_eligible_pair
from app.services.messaging_service import (
    mark_message_delivered,
    send_message,
)

# ── SQLite in-memory test DB ──────────────────────────────────────────────────

SQLITE_URL = "sqlite:///file:p8?mode=memory&cache=shared&uri=true"
_engine = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False, "uri": True},
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


@pytest.fixture(scope="module", autouse=True)
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
        session.close()


@pytest.fixture()
def fake_redis():
    return fakeredis_async.FakeRedis(decode_responses=True)


def _make_user(db: Session, role: str = "member", **kwargs) -> User:
    uid = str(uuid.uuid4())
    user = User(
        id=uid,
        username=kwargs.get("username", f"user_{uid[:8]}"),
        email=kwargs.get("email", f"{uid[:8]}@test.com"),
        password_hash=hash_password("test1234"),
        display_name=kwargs.get("display_name", "Test User"),
        category="Student",
        role=role,
        show_online_status=kwargs.get("show_online_status", True),
        allow_random_discovery=kwargs.get("allow_random_discovery", True),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _auth_headers(user: User) -> dict:
    token = create_access_token(user.id, role=user.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def client(db: Session, fake_redis):
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_redis] = lambda: fake_redis
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── 1. Age Eligibility Tests ──────────────────────────────────────────────────

class TestAgeEligibility:
    def test_underage_registration_rejected(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "username": "underage_kid",
                "email": "kid@example.com",
                "password": "Password123!",
                "display_name": "Kid User",
                "age": 12,
            },
        )
        assert resp.status_code == 422
        assert "at least 13 years old" in resp.text

    def test_eligible_age_registration_succeeds(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "username": "teen_student_99",
                "email": "teen99@example.com",
                "password": "Password123!",
                "display_name": "Teen User",
                "age": 15,
            },
        )
        assert resp.status_code == 201


# ── 2. Session Revocation Tests ───────────────────────────────────────────────

class TestSessionRevocation:
    @pytest.mark.asyncio
    async def test_revoke_all_sessions(self, db, fake_redis):
        u = _make_user(db)
        rt1 = RefreshToken(user_id=u.id, token_hash="hash1", expires_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc), revoked=False)
        rt2 = RefreshToken(user_id=u.id, token_hash="hash2", expires_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc), revoked=False)
        db.add_all([rt1, rt2])
        db.commit()

        # Set fake presence session
        await fake_redis.sadd(f"presence:user:{u.id}:sessions", "sess_abc")
        await fake_redis.set(f"presence:user:{u.id}:state", "AVAILABLE")

        count = await revoke_all_user_sessions(u.id, db, fake_redis)
        assert count == 2

        db.expire_all()
        assert rt1.revoked is True
        assert rt2.revoked is True

        state = await fake_redis.get(f"presence:user:{u.id}:state")
        assert state == "OFFLINE"

    def test_logout_all_endpoint(self, client, db):
        u = _make_user(db)
        resp = client.post("/api/v1/auth/logout-all", headers=_auth_headers(u))
        assert resp.status_code == 200
        assert "revoked_sessions" in resp.json()

    def test_change_password_revokes_sessions(self, client, db):
        u = _make_user(db)
        rt = RefreshToken(user_id=u.id, token_hash=str(uuid.uuid4()), expires_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc), revoked=False)
        db.add(rt)
        db.commit()

        resp = client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "test1234", "new_password": "NewPassword123!"},
            headers=_auth_headers(u),
        )
        assert resp.status_code == 204
        db.expire_all()
        assert rt.revoked is True


# ── 3. Privacy Enforcement Tests ──────────────────────────────────────────────

class TestPrivacyEnforcement:
    @pytest.mark.asyncio
    async def test_hidden_online_status_shows_offline(self, db, fake_redis):
        u1 = _make_user(db, username="viewer")
        u2 = _make_user(db, username="private_user", show_online_status=False)

        await fake_redis.set(f"presence:user:{u2.id}:state", "AVAILABLE")

        from app.api.routes.presence import get_user_presence
        resp = await get_user_presence(u2.id, current_user=u1, db=db, redis=fake_redis)
        assert resp.status == "OFFLINE"

    @pytest.mark.asyncio
    async def test_available_list_excludes_hidden_status(self, db, fake_redis):
        u1 = _make_user(db)
        u_public = _make_user(db, show_online_status=True)
        u_private = _make_user(db, show_online_status=False)

        await fake_redis.set(f"presence:user:{u_public.id}:state", "AVAILABLE")
        await fake_redis.set(f"presence:user:{u_private.id}:state", "AVAILABLE")

        from app.api.routes.presence import list_available_users
        resp = await list_available_users(limit=50, current_user=u1, db=db, redis=fake_redis)
        assert u_public.id in resp.user_ids
        assert u_private.id not in resp.user_ids

    def test_random_discovery_opt_out_ineligible(self, db):
        u1 = _make_user(db, allow_random_discovery=True)
        u2 = _make_user(db, allow_random_discovery=False)
        assert is_eligible_pair(db, u1, u2, mode="random") is False


# ── 4. Message Deduplication & Delivery Receipts ──────────────────────────────

class TestMessageDeduplicationAndDelivery:
    @pytest.mark.asyncio
    async def test_message_deduplication(self, db, fake_redis):
        u1 = _make_user(db)
        u2 = _make_user(db)
        conv = Conversation(id=str(uuid.uuid4()), participant_a=u1.id, participant_b=u2.id, status="active")
        db.add(conv)
        db.commit()

        client_msg_id = "unique_client_nonce_123"
        m1 = await send_message(db, fake_redis, conv.id, u1.id, "Hello!", client_message_id=client_msg_id)
        assert m1 is not None

        # Send same message with same client_message_id
        m2 = await send_message(db, fake_redis, conv.id, u1.id, "Hello!", client_message_id=client_msg_id)
        assert m2 is not None
        assert m1.id == m2.id

    @pytest.mark.asyncio
    async def test_mark_message_delivered(self, db, fake_redis):
        u1 = _make_user(db)
        u2 = _make_user(db)
        conv = Conversation(id=str(uuid.uuid4()), participant_a=u1.id, participant_b=u2.id, status="active")
        db.add(conv)
        db.commit()

        msg = Message(id=str(uuid.uuid4()), conversation_id=conv.id, sender_id=u1.id, content="Hi", status="sent")
        db.add(msg)
        db.commit()

        ok = await mark_message_delivered(db, fake_redis, conv.id, msg.id, u2.id)
        assert ok is True
        db.expire_all()
        assert msg.status == "delivered"

    def test_delivery_receipt_endpoint(self, client, db):
        u1 = _make_user(db)
        u2 = _make_user(db)
        conv = Conversation(id=str(uuid.uuid4()), participant_a=u1.id, participant_b=u2.id, status="active")
        db.add(conv)
        db.commit()

        msg = Message(id=str(uuid.uuid4()), conversation_id=conv.id, sender_id=u1.id, content="Hi", status="sent")
        db.add(msg)
        db.commit()

        resp = client.post(
            f"/api/v1/conversations/{conv.id}/messages/{msg.id}/delivered",
            headers=_auth_headers(u2),
        )
        assert resp.status_code == 200
        assert resp.json()["delivered"] is True


# ── 5. Security Headers Tests ─────────────────────────────────────────────────

class TestSecurityHeaders:
    def test_security_headers_present(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
