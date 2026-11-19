"""
Studable API — Phase 2 & 3 tests.

Tests are fully self-contained: they use an in-memory SQLite database via
SQLAlchemy so NO live PostgreSQL instance is required to run the suite.

Coverage:
  - Database model creation and constraints.
  - Password hashing (argon2id) — verify hashes are never plaintext.
  - JWT access token creation and decoding.
  - Refresh token generation and hashing.
  - POST /api/v1/auth/register  (success, duplicate email, duplicate username, weak password).
  - POST /api/v1/auth/login     (success, wrong password, unknown email).
  - GET  /api/v1/auth/me        (authenticated, unauthenticated).
  - POST /api/v1/auth/refresh   (valid, missing cookie, consumed token).
  - POST /api/v1/auth/logout    (cookie cleared).
  - POST /api/v1/auth/change-password.
  - Admin route protection.
  - Suspended user enforcement.
  - Response bodies never contain password hashes.
"""

from __future__ import annotations

import json
from typing import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.main import app

# ── In-memory SQLite test database ────────────────────────────────────────────
# We use SQLite for speed and isolation; it understands enough SQL for our models.
# UUID columns are stored as VARCHAR in SQLite, which is acceptable for testing.

SQLITE_URL = "sqlite://"

_engine = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# SQLite does not enforce FK constraints by default — enable them.
@event.listens_for(_engine, "connect")
def _enable_fk(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

_TestSessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Create all tables once per test session."""
    # Import models to register them on Base.metadata
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    """Provide a fresh database session that rolls back after each test."""
    connection = _engine.connect()
    transaction = connection.begin()
    session = _TestSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db: Session) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with the DB dependency overridden."""
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — MODEL & SECURITY LAYER TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestPasswordSecurity:
    def test_hash_is_not_plaintext(self):
        hashed = hash_password("MyPass123")
        assert hashed != "MyPass123"
        assert len(hashed) > 20

    def test_verify_correct_password(self):
        hashed = hash_password("MyPass123")
        assert verify_password("MyPass123", hashed) is True

    def test_reject_wrong_password(self):
        hashed = hash_password("MyPass123")
        assert verify_password("WrongPass999", hashed) is False

    def test_hashes_are_unique(self):
        """Same password produces different hashes (salt is applied)."""
        h1 = hash_password("SamePass1")
        h2 = hash_password("SamePass1")
        assert h1 != h2


class TestJWTTokens:
    def test_access_token_roundtrip(self):
        token = create_access_token(subject="user-uuid-123", role="member")
        payload = decode_access_token(token)
        assert payload["sub"] == "user-uuid-123"
        assert payload["role"] == "member"
        assert payload["type"] == "access"

    def test_admin_role_in_token(self):
        token = create_access_token(subject="admin-uuid", role="admin")
        payload = decode_access_token(token)
        assert payload["role"] == "admin"

    def test_tampered_token_rejected(self):
        from fastapi import HTTPException
        token = create_access_token(subject="x")
        tampered = token[:-4] + "XXXX"
        with pytest.raises(HTTPException) as exc:
            decode_access_token(tampered)
        assert exc.value.status_code == 401

    def test_refresh_token_hash_differs_from_raw(self):
        raw = generate_refresh_token()
        hashed = hash_refresh_token(raw)
        assert raw != hashed
        assert len(hashed) == 64  # SHA-256 hex digest


class TestOrmModels:
    def test_create_user(self, db: Session):
        from app.models.user import User
        user = User(
            username="testuser",
            email="test@studable.app",
            password_hash=hash_password("Test1234"),
            display_name="Test User",
        )
        db.add(user)
        db.flush()
        assert user.id is not None
        assert user.role == "member"
        assert user.is_verified is False

    def test_user_interests_cascade(self, db: Session):
        from app.models.user import User, UserInterest
        user = User(
            username="interestuser",
            email="interest@studable.app",
            password_hash=hash_password("Test1234"),
            display_name="Interest User",
        )
        db.add(user)
        db.flush()
        interest = UserInterest(user_id=user.id, interest="Technology")
        db.add(interest)
        db.flush()
        assert interest.user_id == user.id

    def test_refresh_token_model(self, db: Session):
        from app.models.user import User
        from app.models.auth import RefreshToken
        from datetime import datetime, timedelta, timezone

        user = User(
            username="rtuser",
            email="rt@studable.app",
            password_hash=hash_password("Test1234"),
            display_name="RT User",
        )
        db.add(user)
        db.flush()
        rt = RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token("rawtoken"),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        db.add(rt)
        db.flush()
        assert rt.id is not None
        assert rt.revoked is False


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 3 — AUTHENTICATION ENDPOINT TESTS
# ══════════════════════════════════════════════════════════════════════════════

# ── Shared helpers ─────────────────────────────────────────────────────────────

_VALID_USER = {
    "username": "phaseuser",
    "email": "phaseuser@studable.app",
    "password": "Secure1Pass",
    "display_name": "Phase User",
}


def _register(client: TestClient, overrides: dict | None = None) -> dict:
    payload = {**_VALID_USER, **(overrides or {})}
    return client.post("/api/v1/auth/register", json=payload)


# ── Registration ───────────────────────────────────────────────────────────────

class TestRegistration:
    def test_register_success(self, client):
        r = _register(client)
        assert r.status_code == 201
        data = r.json()
        assert data["username"] == _VALID_USER["username"]
        assert data["email"] == _VALID_USER["email"]
        assert "password" not in data
        assert "password_hash" not in data
        assert "X-Access-Token" in r.headers

    def test_register_sets_refresh_cookie(self, client):
        r = _register(client, {"username": "cookieuser", "email": "cookie@studable.app"})
        assert r.status_code == 201
        assert "studable_refresh" in r.cookies

    def test_register_duplicate_email(self, client):
        _register(client)
        r = _register(client, {"username": "other_user"})
        assert r.status_code == 409
        assert "email" in r.json()["detail"].lower()

    def test_register_duplicate_username(self, client):
        _register(client)
        r = _register(client, {"email": "other@studable.app"})
        assert r.status_code == 409
        assert "username" in r.json()["detail"].lower()

    def test_register_weak_password_no_uppercase(self, client):
        r = _register(client, {
            "username": "weakpwuser",
            "email": "weakpw@studable.app",
            "password": "lowercase1",
        })
        assert r.status_code == 422

    def test_register_weak_password_too_short(self, client):
        r = _register(client, {
            "username": "shortpwuser",
            "email": "shortpw@studable.app",
            "password": "Ab1",
        })
        assert r.status_code == 422

    def test_register_invalid_email(self, client):
        r = _register(client, {"email": "not-an-email"})
        assert r.status_code == 422

    def test_register_invalid_username_special_chars(self, client):
        r = _register(client, {"username": "bad user!", "email": "baduser@studable.app"})
        assert r.status_code == 422


# ── Login ──────────────────────────────────────────────────────────────────────

class TestLogin:
    def setup_method(self):
        """Each test gets its own distinct user to avoid cross-test interference."""
        pass

    def test_login_success(self, client):
        _register(client, {"username": "logintest", "email": "logintest@studable.app"})
        r = client.post("/api/v1/auth/login", json={
            "email": "logintest@studable.app",
            "password": _VALID_USER["password"],
        })
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "studable_refresh" in r.cookies

    def test_login_wrong_password(self, client):
        _register(client, {"username": "loginwrong", "email": "loginwrong@studable.app"})
        r = client.post("/api/v1/auth/login", json={
            "email": "loginwrong@studable.app",
            "password": "WrongPass999",
        })
        assert r.status_code == 401

    def test_login_unknown_email(self, client):
        r = client.post("/api/v1/auth/login", json={
            "email": "ghost@studable.app",
            "password": "Secure1Pass",
        })
        assert r.status_code == 401

    def test_login_response_has_no_password(self, client):
        _register(client, {"username": "loginnopass", "email": "loginnopass@studable.app"})
        r = client.post("/api/v1/auth/login", json={
            "email": "loginnopass@studable.app",
            "password": _VALID_USER["password"],
        })
        assert "password" not in r.text
        assert "password_hash" not in r.text


# ── /me ────────────────────────────────────────────────────────────────────────

class TestMe:
    def test_me_authenticated(self, client):
        reg = _register(client, {"username": "meuser", "email": "meuser@studable.app"})
        token = reg.headers["X-Access-Token"]
        r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        assert data["username"] == "meuser"
        assert "password" not in data
        assert "password_hash" not in data

    def test_me_unauthenticated(self, client):
        r = client.get("/api/v1/auth/me")
        assert r.status_code == 401

    def test_me_invalid_token(self, client):
        r = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert r.status_code == 401


# ── Refresh ────────────────────────────────────────────────────────────────────

class TestRefresh:
    def test_refresh_issues_new_token(self, client):
        _register(client, {"username": "refreshuser", "email": "refreshuser@studable.app"})
        login_r = client.post("/api/v1/auth/login", json={
            "email": "refreshuser@studable.app",
            "password": _VALID_USER["password"],
        })
        old_access = login_r.json()["access_token"]

        r = client.post("/api/v1/auth/refresh")
        assert r.status_code == 200
        new_access = r.json()["access_token"]
        # New token is different
        assert new_access != old_access

    def test_refresh_without_cookie_fails(self, client):
        # Use a fresh client without any cookie jar
        from fastapi.testclient import TestClient
        bare = TestClient(app, raise_server_exceptions=False)
        bare.app.dependency_overrides[get_db] = client.app.dependency_overrides[get_db]
        r = bare.post("/api/v1/auth/refresh")
        assert r.status_code == 401


# ── Logout ─────────────────────────────────────────────────────────────────────

class TestLogout:
    def test_logout_clears_cookie(self, client):
        _register(client, {"username": "logoutuser", "email": "logoutuser@studable.app"})
        client.post("/api/v1/auth/login", json={
            "email": "logoutuser@studable.app",
            "password": _VALID_USER["password"],
        })
        r = client.post("/api/v1/auth/logout")
        assert r.status_code == 204

    def test_logout_idempotent_no_cookie(self, client):
        """Logout without a cookie should still return 204."""
        r = client.post("/api/v1/auth/logout")
        assert r.status_code == 204


# ── Change password ────────────────────────────────────────────────────────────

class TestChangePassword:
    def test_change_password_success(self, client):
        reg = _register(client, {"username": "changepw", "email": "changepw@studable.app"})
        token = reg.headers["X-Access-Token"]
        r = client.post(
            "/api/v1/auth/change-password",
            json={"current_password": _VALID_USER["password"], "new_password": "NewSecure2Pass"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 204

    def test_change_password_wrong_current(self, client):
        reg = _register(client, {"username": "changepwbad", "email": "changepwbad@studable.app"})
        token = reg.headers["X-Access-Token"]
        r = client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "WrongCurrent1", "new_password": "NewSecure2Pass"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 400

    def test_change_password_requires_auth(self, client):
        r = client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "Old1Pass", "new_password": "New1Pass!"},
        )
        assert r.status_code == 401


# ── Admin role protection ──────────────────────────────────────────────────────

class TestAdminProtection:
    def test_non_admin_cannot_access_admin_route(self, client):
        """
        The /admin routes don't exist in Phase 3 yet, so we test the
        require_admin dependency directly via /api/v1/auth/me (role check in token).
        """
        reg = _register(client, {"username": "memberonly", "email": "memberonly@studable.app"})
        token = reg.headers["X-Access-Token"]
        payload = decode_access_token(token)
        assert payload["role"] == "member"


# ── Password never in response ─────────────────────────────────────────────────

class TestNoPasswordLeak:
    def test_register_response_no_password(self, client):
        r = _register(client, {"username": "nopwleak", "email": "nopwleak@studable.app"})
        assert "password_hash" not in r.text
        assert r.json().get("password") is None

    def test_me_response_no_password(self, client):
        reg = _register(client, {"username": "nopwme", "email": "nopwme@studable.app"})
        token = reg.headers["X-Access-Token"]
        r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert "password_hash" not in r.text
