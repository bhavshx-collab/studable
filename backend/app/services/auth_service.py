"""
Studable API — Auth service layer.

Business logic for registration, login, token refresh, logout, and
password reset / email verification workflows.

This layer is intentionally decoupled from FastAPI request/response objects
so that it is fully testable without spinning up an HTTP server.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    refresh_token_expiry,
    verify_password,
)
from app.models.auth import RefreshToken
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserMeResponse,
)

logger = logging.getLogger(__name__)

# Pre-computed valid argon2 hash for timing attack defense on non-existent users
_DUMMY_HASH = hash_password("dummy_password_for_timing_defense")


# ── Registration ──────────────────────────────────────────────────────────────

def register_user(payload: RegisterRequest, db: Session) -> tuple[User, str, str]:
    """
    Create a new user account.

    Returns (user, raw_access_token, raw_refresh_token).
    Raises HTTPException 400/409 on validation failures.
    """
    # Normalise email to lower-case for deduplication.
    email = payload.email.lower()
    username = payload.username.lower()

    # Duplicate email check
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email address already exists.",
        )

    # Duplicate username check
    if db.scalar(select(User).where(User.username == username)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That username is already taken.",
        )

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name.strip(),
        role="member",
        is_verified=False,
        is_suspended=False,
    )
    db.add(user)
    db.flush()  # Get user.id without committing yet.

    raw_access = create_access_token(subject=user.id, role=user.role)
    raw_refresh, _ = _create_refresh_token(db, user)

    db.commit()
    db.refresh(user)

    logger.info("New user registered: id=%s username=%s", user.id, user.username)
    return user, raw_access, raw_refresh


# ── Login ─────────────────────────────────────────────────────────────────────

def login_user(payload: LoginRequest, db: Session) -> tuple[User, str, str]:
    """
    Validate credentials and issue a new token pair.

    Deliberately returns the same error for unknown email and wrong password
    to prevent user enumeration.
    """
    email = payload.email.lower()
    user = db.scalar(select(User).where(User.email == email))

    _invalid_creds_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password.",
    )

    if user is None or user.deleted_at is not None:
        # Still run a dummy verify to defend against timing attacks.
        verify_password(payload.password, _DUMMY_HASH)
        raise _invalid_creds_exc

    if not verify_password(payload.password, user.password_hash):
        raise _invalid_creds_exc

    if user.is_suspended:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been suspended. Contact support.",
        )

    raw_access = create_access_token(subject=user.id, role=user.role)
    raw_refresh, _ = _create_refresh_token(db, user)

    db.commit()
    logger.info("User logged in: id=%s", user.id)
    return user, raw_access, raw_refresh


# ── Refresh ───────────────────────────────────────────────────────────────────

def refresh_access_token(raw_refresh: str, db: Session) -> tuple[User, str, str]:
    """
    Validate a refresh token, revoke it (rotation), and issue a new pair.
    """
    token_hash = hash_refresh_token(raw_refresh)
    record = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )

    _invalid_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token.",
    )

    if record is None or record.revoked:
        raise _invalid_exc

    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise _invalid_exc

    # Rotate: revoke old token.
    record.revoked = True
    db.flush()

    user = db.get(User, record.user_id)
    if user is None or user.deleted_at is not None or user.is_suspended:
        raise _invalid_exc

    raw_access = create_access_token(subject=user.id, role=user.role)
    raw_new_refresh, _ = _create_refresh_token(db, user)

    db.commit()
    return user, raw_access, raw_new_refresh


# ── Logout ────────────────────────────────────────────────────────────────────

def logout_user(raw_refresh: str | None, db: Session) -> None:
    """Revoke the supplied refresh token (if present and valid)."""
    if not raw_refresh:
        return
    token_hash = hash_refresh_token(raw_refresh)
    record = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    if record and not record.revoked:
        record.revoked = True
        db.commit()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _create_refresh_token(db: Session, user: User) -> tuple[str, RefreshToken]:
    """Generate, hash, and persist a new refresh token record."""
    raw = generate_refresh_token()
    token_hash = hash_refresh_token(raw)
    record = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=refresh_token_expiry(),
        revoked=False,
    )
    db.add(record)
    db.flush()
    return raw, record
