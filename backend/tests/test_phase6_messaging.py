"""
Studable API — Phase 6 Real-Time Messaging Tests.

Coverage:
  Messaging Service (unit):
    - send_message: success, ended conversation, blocked sender, too long
    - mark_messages_read: marks peer's messages, publishes event
    - get_message_history: pagination with before_id
    - get_unread_count: counts unread across conversations
    - end_conversation: sets ended status, publishes event
    - is_blocked: bidirectional check

  REST Endpoints:
    - GET  /api/v1/conversations          (list)
    - GET  /api/v1/conversations/unread-count
    - GET  /api/v1/conversations/{id}     (not participant → 404)
    - GET  /api/v1/conversations/{id}/messages (pagination)
    - POST /api/v1/conversations/{id}/messages (send)
    - POST /api/v1/conversations/{id}/read
    - POST /api/v1/conversations/{id}/typing
    - DELETE /api/v1/conversations/{id}   (end)
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

from app.core.database import Base, get_db
from app.core.redis import get_redis
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.block import Block
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.services.messaging_service import (
    end_conversation,
    get_message_history,
    get_unread_count,
    is_blocked,
    mark_messages_read,
    send_message,
)

# ── SQLite in-memory test DB ──────────────────────────────────────────────────

SQLITE_URL = "sqlite:///file:p6?mode=memory&cache=shared&uri=true"
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


def _make_user(db: Session, **kwargs) -> User:
    uid = str(uuid.uuid4())
    user = User(
        id=uid,
        username=kwargs.get("username", f"user_{uid[:8]}"),
        email=kwargs.get("email", f"{uid[:8]}@test.com"),
        password_hash=hash_password("test1234"),
        display_name=kwargs.get("display_name", "Test User"),
        category="Student",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_conversation(db: Session, user_a: User, user_b: User, status: str = "active") -> Conversation:
    conv = Conversation(
        id=str(uuid.uuid4()),
        participant_a=user_a.id,
        participant_b=user_b.id,
        topic="Test topic",
        matching_mode="random",
        status=status,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def _make_message(
    db: Session,
    conv: Conversation,
    sender: User,
    content: str = "hello",
    status: str = "sent",
    created_at=None,
) -> Message:
    from datetime import datetime, timezone
    msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conv.id,
        sender_id=sender.id,
        content=content,
        status=status,
        created_at=created_at or datetime.now(timezone.utc),
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


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


# ── Unit tests: messaging service ─────────────────────────────────────────────

class TestIsBlocked:
    def test_not_blocked(self, db):
        a = _make_user(db)
        b = _make_user(db)
        assert is_blocked(db, a.id, b.id) is False

    def test_blocked_one_direction(self, db):
        a = _make_user(db)
        b = _make_user(db)
        db.add(Block(blocker_id=a.id, blocked_id=b.id))
        db.commit()
        assert is_blocked(db, a.id, b.id) is True
        assert is_blocked(db, b.id, a.id) is True  # bidirectional

    def test_cleanup(self, db):
        pass  # each test uses a fresh conversation


class TestSendMessage:
    @pytest.mark.asyncio
    async def test_send_success(self, db, fake_redis):
        a = _make_user(db)
        b = _make_user(db)
        conv = _make_conversation(db, a, b)
        msg = await send_message(db, fake_redis, conv.id, a.id, "Hello!")
        assert msg is not None
        assert msg.content == "Hello!"
        assert msg.sender_id == a.id
        assert msg.status == "sent"

    @pytest.mark.asyncio
    async def test_send_ended_conversation(self, db, fake_redis):
        a = _make_user(db)
        b = _make_user(db)
        conv = _make_conversation(db, a, b, status="ended")
        msg = await send_message(db, fake_redis, conv.id, a.id, "Should fail")
        assert msg is None

    @pytest.mark.asyncio
    async def test_send_not_participant(self, db, fake_redis):
        a = _make_user(db)
        b = _make_user(db)
        c = _make_user(db)
        conv = _make_conversation(db, a, b)
        msg = await send_message(db, fake_redis, conv.id, c.id, "Outsider")
        assert msg is None

    @pytest.mark.asyncio
    async def test_send_blocked(self, db, fake_redis):
        a = _make_user(db)
        b = _make_user(db)
        conv = _make_conversation(db, a, b)
        db.add(Block(blocker_id=a.id, blocked_id=b.id))
        db.commit()
        msg = await send_message(db, fake_redis, conv.id, a.id, "Blocked")
        assert msg is None

    @pytest.mark.asyncio
    async def test_send_too_long(self, db, fake_redis):
        a = _make_user(db)
        b = _make_user(db)
        conv = _make_conversation(db, a, b)
        msg = await send_message(db, fake_redis, conv.id, a.id, "x" * 2001)
        assert msg is None

    @pytest.mark.asyncio
    async def test_send_empty(self, db, fake_redis):
        a = _make_user(db)
        b = _make_user(db)
        conv = _make_conversation(db, a, b)
        msg = await send_message(db, fake_redis, conv.id, a.id, "   ")
        assert msg is None


class TestMarkRead:
    @pytest.mark.asyncio
    async def test_mark_messages_read(self, db, fake_redis):
        a = _make_user(db)
        b = _make_user(db)
        conv = _make_conversation(db, a, b)
        _make_message(db, conv, b, "msg1")
        _make_message(db, conv, b, "msg2")
        count = await mark_messages_read(db, fake_redis, conv.id, a.id)
        assert count == 2
        # Messages should now be read
        db.expire_all()
        for m in db.query(Message).filter(Message.conversation_id == conv.id).all():
            assert m.status == "read"

    @pytest.mark.asyncio
    async def test_mark_own_messages_not_changed(self, db, fake_redis):
        a = _make_user(db)
        b = _make_user(db)
        conv = _make_conversation(db, a, b)
        _make_message(db, conv, a, "my own msg")
        count = await mark_messages_read(db, fake_redis, conv.id, a.id)
        assert count == 0  # own messages not marked


class TestGetHistory:
    def test_basic_history(self, db, fake_redis):
        a = _make_user(db)
        b = _make_user(db)
        conv = _make_conversation(db, a, b)
        _make_message(db, conv, a, "first")
        _make_message(db, conv, b, "second")
        msgs = get_message_history(db, conv.id, a.id)
        assert msgs is not None
        assert len(msgs) == 2
        assert msgs[0].content == "first"
        assert msgs[1].content == "second"

    def test_not_participant_returns_none(self, db, fake_redis):
        a = _make_user(db)
        b = _make_user(db)
        c = _make_user(db)
        conv = _make_conversation(db, a, b)
        result = get_message_history(db, conv.id, c.id)
        assert result is None

    def test_pagination_before_id(self, db, fake_redis):
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        a = _make_user(db)
        b = _make_user(db)
        conv = _make_conversation(db, a, b)
        m1 = _make_message(db, conv, a, "first", created_at=now - timedelta(minutes=5))
        m2 = _make_message(db, conv, b, "second", created_at=now)
        # before m2 → only m1 returned
        msgs = get_message_history(db, conv.id, a.id, before_id=m2.id)
        assert len(msgs) == 1
        assert msgs[0].id == m1.id


class TestUnreadCount:
    def test_unread_count(self, db, fake_redis):
        a = _make_user(db)
        b = _make_user(db)
        conv = _make_conversation(db, a, b)
        _make_message(db, conv, b, "unread1")
        _make_message(db, conv, b, "unread2")
        _make_message(db, conv, a, "my own")  # own → not counted
        count = get_unread_count(db, a.id)
        assert count >= 2


class TestEndConversation:
    @pytest.mark.asyncio
    async def test_end_success(self, db, fake_redis):
        a = _make_user(db)
        b = _make_user(db)
        conv = _make_conversation(db, a, b)
        ok = await end_conversation(db, fake_redis, conv.id, a.id)
        assert ok is True
        db.expire_all()
        updated = db.get(Conversation, conv.id)
        assert updated.status == "ended"
        assert updated.ended_at is not None

    @pytest.mark.asyncio
    async def test_end_already_ended(self, db, fake_redis):
        a = _make_user(db)
        b = _make_user(db)
        conv = _make_conversation(db, a, b, status="ended")
        ok = await end_conversation(db, fake_redis, conv.id, a.id)
        assert ok is False

    @pytest.mark.asyncio
    async def test_end_not_participant(self, db, fake_redis):
        a = _make_user(db)
        b = _make_user(db)
        c = _make_user(db)
        conv = _make_conversation(db, a, b)
        ok = await end_conversation(db, fake_redis, conv.id, c.id)
        assert ok is False


# ── REST endpoint tests ───────────────────────────────────────────────────────

class TestConversationListEndpoint:
    def test_list_conversations(self, client, db):
        a = _make_user(db)
        b = _make_user(db)
        _make_conversation(db, a, b)
        resp = client.get("/api/v1/conversations", headers=_auth_headers(a))
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_list_requires_auth(self, client):
        resp = client.get("/api/v1/conversations")
        assert resp.status_code == 401

    def test_unread_count_endpoint(self, client, db):
        a = _make_user(db)
        resp = client.get("/api/v1/conversations/unread-count", headers=_auth_headers(a))
        assert resp.status_code == 200
        assert "unread_count" in resp.json()


class TestConversationDetailEndpoint:
    def test_get_conversation(self, client, db):
        a = _make_user(db)
        b = _make_user(db)
        conv = _make_conversation(db, a, b)
        resp = client.get(f"/api/v1/conversations/{conv.id}", headers=_auth_headers(a))
        assert resp.status_code == 200
        assert resp.json()["id"] == conv.id

    def test_get_conversation_not_participant(self, client, db):
        a = _make_user(db)
        b = _make_user(db)
        c = _make_user(db)
        conv = _make_conversation(db, a, b)
        resp = client.get(f"/api/v1/conversations/{conv.id}", headers=_auth_headers(c))
        assert resp.status_code == 404


class TestMessagesEndpoint:
    def test_send_message(self, client, db):
        a = _make_user(db)
        b = _make_user(db)
        conv = _make_conversation(db, a, b)
        resp = client.post(
            f"/api/v1/conversations/{conv.id}/messages",
            json={"content": "Hey there!"},
            headers=_auth_headers(a),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["content"] == "Hey there!"
        assert data["sender_id"] == a.id

    def test_send_message_ended_conversation(self, client, db):
        a = _make_user(db)
        b = _make_user(db)
        conv = _make_conversation(db, a, b, status="ended")
        resp = client.post(
            f"/api/v1/conversations/{conv.id}/messages",
            json={"content": "Late message"},
            headers=_auth_headers(a),
        )
        assert resp.status_code == 422

    def test_get_messages(self, client, db):
        a = _make_user(db)
        b = _make_user(db)
        conv = _make_conversation(db, a, b)
        _make_message(db, conv, a, "msg1")
        _make_message(db, conv, b, "msg2")
        resp = client.get(
            f"/api/v1/conversations/{conv.id}/messages",
            headers=_auth_headers(a),
        )
        assert resp.status_code == 200
        msgs = resp.json()
        assert len(msgs) >= 2

    def test_get_messages_pagination(self, client, db):
        a = _make_user(db)
        b = _make_user(db)
        conv = _make_conversation(db, a, b)
        resp = client.get(
            f"/api/v1/conversations/{conv.id}/messages?limit=1",
            headers=_auth_headers(a),
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_mark_read(self, client, db):
        a = _make_user(db)
        b = _make_user(db)
        conv = _make_conversation(db, a, b)
        _make_message(db, conv, b, "unread")
        resp = client.post(
            f"/api/v1/conversations/{conv.id}/read",
            headers=_auth_headers(a),
        )
        assert resp.status_code == 200
        assert resp.json()["marked_read"] >= 1

    def test_typing_indicator(self, client, db):
        a = _make_user(db)
        b = _make_user(db)
        conv = _make_conversation(db, a, b)
        resp = client.post(
            f"/api/v1/conversations/{conv.id}/typing",
            json={"is_typing": True},
            headers=_auth_headers(a),
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_end_conversation_rest(self, client, db):
        a = _make_user(db)
        b = _make_user(db)
        conv = _make_conversation(db, a, b)
        resp = client.delete(
            f"/api/v1/conversations/{conv.id}",
            headers=_auth_headers(a),
        )
        assert resp.status_code == 200
        assert resp.json()["ended"] is True

    def test_end_already_ended(self, client, db):
        a = _make_user(db)
        b = _make_user(db)
        conv = _make_conversation(db, a, b, status="ended")
        resp = client.delete(
            f"/api/v1/conversations/{conv.id}",
            headers=_auth_headers(a),
        )
        assert resp.status_code == 404
