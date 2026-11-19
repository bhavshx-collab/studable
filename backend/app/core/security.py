"""
Studable API — Security utilities.

Responsibilities:
- Argon2id password hashing (via passlib).
- JWT access token creation and verification.
- Opaque refresh token generation and hashing.
- Cookie helpers for the refresh token.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, Request, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ── Password hashing ─────────────────────────────────────────────────────────
# argon2 is the default; bcrypt is a fallback for any legacy records.
_pwd_ctx = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Return an Argon2id hash of *plain*. Never store raw passwords."""
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed*."""
    return _pwd_ctx.verify(plain, hashed)


# ── JWT access tokens ─────────────────────────────────────────────────────────

def create_access_token(
    subject: str,
    role: str = "member",
    extra: dict[str, Any] | None = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        subject: The user's UUID (stored in ``sub`` claim).
        role:    The user's role (``member`` | ``admin``).
        extra:   Optional extra claims merged into the payload.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "jti": secrets.token_hex(16),
        "iat": now,
        "exp": expire,
        "type": "access",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.

    Raises HTTPException 401 on any verification failure.
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != "access":
            raise credentials_exc
        sub: str | None = payload.get("sub")
        if sub is None:
            raise credentials_exc
        return payload
    except JWTError:
        raise credentials_exc


# ── Opaque refresh tokens ─────────────────────────────────────────────────────

def generate_refresh_token() -> str:
    """Return a 64-byte URL-safe random token (sent to the client)."""
    return secrets.token_urlsafe(64)


def hash_refresh_token(raw_token: str) -> str:
    """Return the SHA-256 hex digest of *raw_token* (stored in the DB)."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


def refresh_token_expiry() -> datetime:
    """Return the UTC datetime when a new refresh token expires."""
    return datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)


# ── Cookie helpers ─────────────────────────────────────────────────────────────

def set_refresh_cookie(response: Any, raw_token: str) -> None:
    """Write the refresh token into an HttpOnly cookie on *response*."""
    from datetime import timedelta

    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
        max_age=int(timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS).total_seconds()),
        path="/",
    )


def clear_refresh_cookie(response: Any) -> None:
    """Remove the refresh token cookie from *response*."""
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
        path="/",
    )


def get_refresh_token_from_cookie(request: Request) -> str | None:
    """Extract the raw refresh token from the incoming request cookie."""
    return request.cookies.get(settings.REFRESH_COOKIE_NAME)
