"""
Studable API — Phase 7 Safety, Moderation & Testing Tests.

Coverage:
  Blocking:
    - POST /api/v1/users/{id}/block    (block a user)
    - DELETE /api/v1/users/{id}/block  (unblock)
    - GET  /api/v1/blocks              (list blocked)
    - Block prevents messaging (service level)
    - Cannot block yourself
    - Duplicate block idempotent

  Reporting:
    - POST /api/v1/users/{id}/report   (submit report)
    - Cannot report yourself

  Admin:
    - GET  /api/v1/admin/reports       (list, pagination, status filter)
    - POST /api/v1/admin/reports/{id}/resolve
    - GET  /api/v1/admin/users         (list, search)
    - POST /api/v1/admin/users/{id}/suspend
    - DELETE /api/v1/admin/users/{id}/suspend
    - GET  /api/v1/admin/metrics
    - Non-admin gets 403

  Privacy:
    - PATCH /api/v1/users/me/privacy

  Account deletion:
    - DELETE /api/v1/users/me (soft-delete)
    - Deleted user cannot log in

  Password reset:
    - POST /api/v1/auth/forgot-password
    - POST /api/v1/auth/reset-password

  Suspended user:
    - Suspended user gets 403 on protected routes
"""

from __future__ import annotations

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
from app.models.report import Report
from app.models.user import User

# ── SQLite in-memory test DB ──────────────────────────────────────────────────

SQLITE_URL = "sqlite:///file:p7?mode=memory&cache=shared&uri=true"
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
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_admin(db: Session) -> User:
    return _make_user(db, role="admin")


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


# ── Block tests ──────────────────────────────────────────────────────────────

class TestBlocking:
    def test_block_user(self, client, db):
        a = _make_user(db)
        b = _make_user(db)
        resp = client.post(f"/api/v1/users/{b.id}/block", headers=_auth_headers(a))
        assert resp.status_code == 201
        assert resp.json()["blocked"] is True

    def test_block_idempotent(self, client, db):
        a = _make_user(db)
        b = _make_user(db)
        client.post(f"/api/v1/users/{b.id}/block", headers=_auth_headers(a))
        resp = client.post(f"/api/v1/users/{b.id}/block", headers=_auth_headers(a))
        assert resp.status_code == 201
        assert resp.json().get("already_blocked") is True

    def test_cannot_block_self(self, client, db):
        a = _make_user(db)
        resp = client.post(f"/api/v1/users/{a.id}/block", headers=_auth_headers(a))
        assert resp.status_code == 400

    def test_unblock_user(self, client, db):
        a = _make_user(db)
        b = _make_user(db)
        client.post(f"/api/v1/users/{b.id}/block", headers=_auth_headers(a))
        resp = client.delete(f"/api/v1/users/{b.id}/block", headers=_auth_headers(a))
        assert resp.status_code == 200
        assert resp.json()["unblocked"] is True

    def test_unblock_not_found(self, client, db):
        a = _make_user(db)
        b = _make_user(db)
        resp = client.delete(f"/api/v1/users/{b.id}/block", headers=_auth_headers(a))
        assert resp.status_code == 404

    def test_list_blocks(self, client, db):
        a = _make_user(db)
        b = _make_user(db)
        client.post(f"/api/v1/users/{b.id}/block", headers=_auth_headers(a))
        resp = client.get("/api/v1/blocks", headers=_auth_headers(a))
        assert resp.status_code == 200
        ids = [row["blocked_id"] for row in resp.json()]
        assert b.id in ids

    def test_block_prevents_messaging(self, client, db):
        """Block enforced at the service level (via is_blocked check in send_message)."""
        from app.services.messaging_service import is_blocked
        a = _make_user(db)
        b = _make_user(db)
        db.add(Block(blocker_id=a.id, blocked_id=b.id))
        db.commit()
        assert is_blocked(db, a.id, b.id) is True
        assert is_blocked(db, b.id, a.id) is True

    def test_block_requires_auth(self, client, db):
        b = _make_user(db)
        resp = client.post(f"/api/v1/users/{b.id}/block")
        assert resp.status_code == 401


# ── Report tests ──────────────────────────────────────────────────────────────

class TestReporting:
    def test_report_user(self, client, db):
        a = _make_user(db)
        b = _make_user(db)
        resp = client.post(
            f"/api/v1/users/{b.id}/report",
            json={"reason": "Harassment", "details": "Was mean"},
            headers=_auth_headers(a),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["reported_user_id"] == b.id
        assert data["status"] == "pending"
        assert data["reason"] == "Harassment"

    def test_cannot_report_self(self, client, db):
        a = _make_user(db)
        resp = client.post(
            f"/api/v1/users/{a.id}/report",
            json={"reason": "Spam"},
            headers=_auth_headers(a),
        )
        assert resp.status_code == 400

    def test_report_nonexistent_user(self, client, db):
        a = _make_user(db)
        resp = client.post(
            f"/api/v1/users/{uuid.uuid4()}/report",
            json={"reason": "Spam"},
            headers=_auth_headers(a),
        )
        assert resp.status_code == 404


# ── Admin tests ───────────────────────────────────────────────────────────────

class TestAdminReports:
    def test_list_reports_as_admin(self, client, db):
        admin = _make_admin(db)
        a = _make_user(db)
        b = _make_user(db)
        db.add(Report(id=str(uuid.uuid4()), reporter_id=a.id, reported_user_id=b.id, reason="Spam"))
        db.commit()
        resp = client.get("/api/v1/admin/reports", headers=_auth_headers(admin))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_reports_non_admin_forbidden(self, client, db):
        member = _make_user(db)
        resp = client.get("/api/v1/admin/reports", headers=_auth_headers(member))
        assert resp.status_code == 403

    def test_resolve_report_dismiss(self, client, db):
        admin = _make_admin(db)
        a = _make_user(db)
        b = _make_user(db)
        report = Report(id=str(uuid.uuid4()), reporter_id=a.id, reported_user_id=b.id, reason="Spam")
        db.add(report)
        db.commit()
        resp = client.post(
            f"/api/v1/admin/reports/{report.id}/resolve",
            json={"action": "dismissed"},
            headers=_auth_headers(admin),
        )
        assert resp.status_code == 200
        assert resp.json()["action"] == "dismissed"

    def test_resolve_report_suspend(self, client, db):
        admin = _make_admin(db)
        a = _make_user(db)
        b = _make_user(db)
        report = Report(id=str(uuid.uuid4()), reporter_id=a.id, reported_user_id=b.id, reason="Harassment")
        db.add(report)
        db.commit()
        resp = client.post(
            f"/api/v1/admin/reports/{report.id}/resolve",
            json={"action": "resolved_suspended"},
            headers=_auth_headers(admin),
        )
        assert resp.status_code == 200
        db.expire_all()
        b_updated = db.get(User, b.id)
        assert b_updated.is_suspended is True

    def test_resolve_already_resolved(self, client, db):
        admin = _make_admin(db)
        a = _make_user(db)
        b = _make_user(db)
        report = Report(
            id=str(uuid.uuid4()),
            reporter_id=a.id,
            reported_user_id=b.id,
            reason="Spam",
            status="dismissed",
        )
        db.add(report)
        db.commit()
        resp = client.post(
            f"/api/v1/admin/reports/{report.id}/resolve",
            json={"action": "dismissed"},
            headers=_auth_headers(admin),
        )
        assert resp.status_code == 409

    def test_invalid_action(self, client, db):
        admin = _make_admin(db)
        a = _make_user(db)
        b = _make_user(db)
        report = Report(id=str(uuid.uuid4()), reporter_id=a.id, reported_user_id=b.id, reason="Spam")
        db.add(report)
        db.commit()
        resp = client.post(
            f"/api/v1/admin/reports/{report.id}/resolve",
            json={"action": "invalid_action"},
            headers=_auth_headers(admin),
        )
        assert resp.status_code == 400


class TestAdminUsers:
    def test_list_users(self, client, db):
        admin = _make_admin(db)
        resp = client.get("/api/v1/admin/users", headers=_auth_headers(admin))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_search_users(self, client, db):
        admin = _make_admin(db)
        unique = _make_user(db, username="unique_search_xyz")
        resp = client.get("/api/v1/admin/users?q=unique_search_xyz", headers=_auth_headers(admin))
        assert resp.status_code == 200
        ids = [u["id"] for u in resp.json()]
        assert unique.id in ids

    def test_suspend_user(self, client, db):
        admin = _make_admin(db)
        member = _make_user(db)
        resp = client.post(f"/api/v1/admin/users/{member.id}/suspend", headers=_auth_headers(admin))
        assert resp.status_code == 200
        assert resp.json()["suspended"] is True
        db.expire_all()
        assert db.get(User, member.id).is_suspended is True

    def test_suspend_self_forbidden(self, client, db):
        admin = _make_admin(db)
        resp = client.post(f"/api/v1/admin/users/{admin.id}/suspend", headers=_auth_headers(admin))
        assert resp.status_code == 400

    def test_unsuspend_user(self, client, db):
        admin = _make_admin(db)
        member = _make_user(db)
        member.is_suspended = True
        db.commit()
        resp = client.delete(f"/api/v1/admin/users/{member.id}/suspend", headers=_auth_headers(admin))
        assert resp.status_code == 200
        assert resp.json()["unsuspended"] is True
        db.expire_all()
        assert db.get(User, member.id).is_suspended is False

    def test_metrics(self, client, db):
        admin = _make_admin(db)
        resp = client.get("/api/v1/admin/metrics", headers=_auth_headers(admin))
        assert resp.status_code == 200
        data = resp.json()
        for key in ("total_users", "suspended_users", "total_conversations", "pending_reports", "total_matches"):
            assert key in data

    def test_metrics_non_admin_forbidden(self, client, db):
        member = _make_user(db)
        resp = client.get("/api/v1/admin/metrics", headers=_auth_headers(member))
        assert resp.status_code == 403


# ── Privacy & Account Deletion ────────────────────────────────────────────────

class TestPrivacySettings:
    def test_update_privacy(self, client, db):
        a = _make_user(db)
        resp = client.patch(
            "/api/v1/users/me/privacy",
            json={"show_online_status": False, "allow_random_discovery": False},
            headers=_auth_headers(a),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["show_online_status"] is False
        assert data["allow_random_discovery"] is False

    def test_update_privacy_partial(self, client, db):
        a = _make_user(db)
        resp = client.patch(
            "/api/v1/users/me/privacy",
            json={"show_online_status": True},
            headers=_auth_headers(a),
        )
        assert resp.status_code == 200
        assert resp.json()["show_online_status"] is True


class TestAccountDeletion:
    def test_delete_account(self, client, db):
        a = _make_user(db)
        resp = client.delete("/api/v1/users/me", headers=_auth_headers(a))
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True
        db.expire_all()
        user = db.get(User, a.id)
        assert user.deleted_at is not None

    def test_deleted_user_cannot_access(self, client, db):
        a = _make_user(db)
        # Soft-delete the user
        a.deleted_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        db.commit()
        # Token still valid but user won't be found
        resp = client.get("/api/v1/conversations", headers=_auth_headers(a))
        assert resp.status_code == 401


# ── Password Reset ────────────────────────────────────────────────────────────

class TestPasswordReset:
    def test_forgot_password_returns_200_always(self, client, db):
        """Always returns 200 to prevent user enumeration."""
        resp = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nonexistent@example.com"},
        )
        assert resp.status_code == 200

    def test_reset_password_flow(self, client, db):
        """Full reset flow: request token via forgot-password, reset password."""
        a = _make_user(db)
        resp = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": a.email},
        )
        assert resp.status_code == 200
        token = resp.json().get("dev_token")
        assert token is not None

        resp2 = client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "new_password": "NewPassword123!"},
        )
        assert resp2.status_code == 200
        assert "successfully" in resp2.json()["detail"]

    def test_reset_invalid_token(self, client, db):
        resp = client.post(
            "/api/v1/auth/reset-password",
            json={"token": "bogus_token", "new_password": "NewPass123!"},
        )
        assert resp.status_code == 400


# ── Suspended user ─────────────────────────────────────────────────────────────

class TestSuspendedUser:
    def test_suspended_user_gets_403(self, client, db):
        a = _make_user(db)
        a.is_suspended = True
        db.commit()
        resp = client.get("/api/v1/conversations", headers=_auth_headers(a))
        assert resp.status_code == 403
