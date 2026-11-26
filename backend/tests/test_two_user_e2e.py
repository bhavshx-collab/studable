"""
Studable API — Two-User End-to-End Integration Test.

Simulates the complete user lifecycle across two independent users:
  1. Registration & Authentication (Age-gated, JWT tokens)
  2. Profile & Presence Configuration
  3. Real-Time Matching & Proposal Acceptance
  4. Conversation & Messaging (Send, Deliver, Read, Deduplication, History)
  5. Safety: Reporting, Blocking, and Moderation
  6. Admin Suspension & Immediate Session Revocation
"""

from __future__ import annotations

import asyncio
import uuid
import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
import fakeredis.aioredis as fakeredis_async

from app.core.database import Base, get_db
from app.core.redis import get_redis
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.user import User
from app.models.conversation import Conversation
from app.services.matching_service import (
    accept_match,
    join_queue,
    propose_match,
)
from app.services.presence_service import (
    PresenceStatus,
    set_presence_validated,
)

# In-memory shared SQLite
SQLITE_URL = "sqlite:///file:two_user_e2e?mode=memory&cache=shared&uri=true"
_engine = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False, "uri": True},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture
def db():
    connection = _engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def fake_redis():
    return fakeredis_async.FakeRedis(decode_responses=True)


@pytest.mark.asyncio
async def test_complete_two_user_lifecycle(db, fake_redis):
    """
    Complete end-to-end flow:
    Register -> Match -> Message -> Deliver/Read -> Report/Block -> Admin Suspend.
    """
    def override_get_db():
        yield db

    async def override_get_redis():
        yield fake_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # ── 1. Register User A and User B ──────────────────────────────────────
        reg_a = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "alice_e2e",
                "email": "alice_e2e@example.com",
                "password": "Password123!",
                "display_name": "Alice Developer",
                "age": 21,
            },
        )
        assert reg_a.status_code == 201, reg_a.text
        user_a_id = reg_a.json()["id"]

        reg_b = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "bob_e2e",
                "email": "bob_e2e@example.com",
                "password": "Password123!",
                "display_name": "Bob Designer",
                "age": 22,
            },
        )
        assert reg_b.status_code == 201, reg_b.text
        user_b_id = reg_b.json()["id"]

        # Also create an admin user
        admin_user = User(
            id=str(uuid.uuid4()),
            username="admin_e2e",
            email="admin_e2e@example.com",
            password_hash=hash_password("AdminPass123!"),
            display_name="Admin Moderator",
            role="admin",
            is_verified=True,
        )
        db.add(admin_user)
        db.commit()

        # ── 2. Authenticate Users ──────────────────────────────────────────────
        token_a = create_access_token(user_a_id, role="member")
        token_b = create_access_token(user_b_id, role="member")
        token_admin = create_access_token(admin_user.id, role="admin")

        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}
        headers_admin = {"Authorization": f"Bearer {token_admin}"}

        # ── 3. Presence & Matching Queue ───────────────────────────────────────
        await set_presence_validated(fake_redis, user_a_id, PresenceStatus.ONLINE)
        await set_presence_validated(fake_redis, user_a_id, PresenceStatus.AVAILABLE)
        await set_presence_validated(fake_redis, user_b_id, PresenceStatus.ONLINE)
        await set_presence_validated(fake_redis, user_b_id, PresenceStatus.AVAILABLE)

        ok_a, _, info_a = await join_queue(fake_redis, db, user_a_id, "random")
        assert ok_a is True
        assert info_a["status"] == "QUEUED"

        ok_b, _, info_b = await join_queue(fake_redis, db, user_b_id, "random")
        assert ok_b is True
        assert info_b["status"] == "QUEUED"

        # Match proposal generated between Alice and Bob
        user_a = db.get(User, user_a_id)
        user_b = db.get(User, user_b_id)
        match_id = await propose_match(fake_redis, db, user_a, user_b, mode="random")
        assert match_id is not None

        # Alice accepts
        ok_acc_a, _, acc_info_a = await accept_match(fake_redis, db, user_a_id, match_id)
        assert ok_acc_a is True
        assert acc_info_a["status"] == "ACCEPTED"
        assert acc_info_a["awaiting_peer"] is True

        # Bob accepts -> mutual acceptance creates conversation
        ok_acc_b, _, acc_info_b = await accept_match(fake_redis, db, user_b_id, match_id)
        assert ok_acc_b is True
        assert acc_info_b["status"] == "COMPLETED"
        assert "conversation_id" in acc_info_b
        conv_id = acc_info_b["conversation_id"]

        # ── 4. Messaging ───────────────────────────────────────────────────────
        # Alice sends a message to Bob
        client_msg_id = f"client-msg-{uuid.uuid4()}"
        msg_send_res = await client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers=headers_a,
            json={
                "content": "Hi Bob! Great to connect on Studable.",
                "client_message_id": client_msg_id,
            },
        )
        assert msg_send_res.status_code == 201, msg_send_res.text
        msg_data = msg_send_res.json()
        msg_id = msg_data["id"]
        assert msg_data["content"] == "Hi Bob! Great to connect on Studable."
        assert msg_data["status"] == "sent"

        # Message deduplication check: re-sending the same client_message_id is idempotent
        dedup_res = await client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers=headers_a,
            json={
                "content": "Hi Bob! Great to connect on Studable.",
                "client_message_id": client_msg_id,
            },
        )
        assert dedup_res.status_code in (200, 201)
        assert dedup_res.json()["id"] == msg_id

        # Bob checks unread count -> should be 1
        unread_res = await client.get("/api/v1/conversations/unread-count", headers=headers_b)
        assert unread_res.status_code == 200
        assert unread_res.json()["unread_count"] == 1

        # Bob marks message as delivered
        deliv_res = await client.post(
            f"/api/v1/conversations/{conv_id}/messages/{msg_id}/delivered",
            headers=headers_b,
        )
        assert deliv_res.status_code == 200
        assert deliv_res.json()["delivered"] is True

        # Bob marks conversation read
        read_res = await client.post(f"/api/v1/conversations/{conv_id}/read", headers=headers_b)
        assert read_res.status_code == 200
        assert read_res.json()["marked_read"] >= 1

        # Bob checks unread count again -> now 0
        unread_res2 = await client.get("/api/v1/conversations/unread-count", headers=headers_b)
        assert unread_res2.status_code == 200
        assert unread_res2.json()["unread_count"] == 0

        # ── 5. Safety: Reporting & Blocking ────────────────────────────────────
        # Bob reports Alice for spam
        report_res = await client.post(
            f"/api/v1/users/{user_a_id}/report",
            headers=headers_b,
            json={
                "reason": "Spam",
                "details": "Promotional unsolicited link in chat",
            },
        )
        assert report_res.status_code == 201, report_res.text
        report_id = report_res.json()["id"]

        # Bob blocks Alice
        block_res = await client.post(
            f"/api/v1/users/{user_a_id}/block",
            headers=headers_b,
        )
        assert block_res.status_code == 201

        # Alice attempts to message Bob -> rejected due to block
        blocked_send = await client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers=headers_a,
            json={"content": "Can you still see this?"},
        )
        assert blocked_send.status_code == 422
        assert "blocked" in blocked_send.json()["detail"].lower()

        # ── 6. Admin Moderation & Session Revocation ────────────────────────────
        # Admin inspects reports
        reports_res = await client.get("/api/v1/admin/reports", headers=headers_admin)
        assert reports_res.status_code == 200
        reports = reports_res.json()
        assert any(r["id"] == report_id for r in reports)

        # Admin resolves report and suspends Alice
        resolve_res = await client.post(
            f"/api/v1/admin/reports/{report_id}/resolve",
            headers=headers_admin,
            json={"action": "resolved_suspended"},
        )
        assert resolve_res.status_code == 200

        # Verify Alice's status in DB is is_suspended=True
        db.expire_all()
        user_a_db = db.get(User, user_a_id)
        assert user_a_db.is_suspended is True

        # Verify Alice's session was revoked in Redis and state set to OFFLINE
        presence_state = await fake_redis.get(f"presence:user:{user_a_id}:state")
        assert presence_state == "OFFLINE"

    app.dependency_overrides.clear()
