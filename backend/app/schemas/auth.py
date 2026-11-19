"""
Studable API — Auth Pydantic schemas.

Request bodies and response models for authentication endpoints.
Passwords are NEVER included in response models.
"""

from __future__ import annotations

import re
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Validation helpers ────────────────────────────────────────────────────────

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,32}$")


def _validate_password_strength(value: str) -> str:
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if not re.search(r"[A-Z]", value):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", value):
        raise ValueError("Password must contain at least one lowercase letter.")
    if not re.search(r"\d", value):
        raise ValueError("Password must contain at least one number.")
    return value


# ── Registration ──────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: Annotated[str, Field(min_length=3, max_length=32)]
    email: EmailStr
    password: Annotated[str, Field(min_length=8, max_length=128)]
    display_name: Annotated[str, Field(min_length=1, max_length=80)]

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not _USERNAME_RE.match(v):
            raise ValueError(
                "Username must be 3–32 characters and contain only "
                "letters, numbers, and underscores."
            )
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _validate_password_strength(v)


class RegisterResponse(BaseModel):
    id: str
    username: str
    email: str
    display_name: str
    role: str

    model_config = {"from_attributes": True}


# ── Login ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Returned on successful login or token refresh."""
    access_token: str
    token_type: str = "bearer"


# ── Password reset / change ───────────────────────────────────────────────────

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: Annotated[str, Field(min_length=8, max_length=128)]

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return _validate_password_strength(v)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: Annotated[str, Field(min_length=8, max_length=128)]

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return _validate_password_strength(v)


# ── Email verification ────────────────────────────────────────────────────────

class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


# ── Current user (me) ─────────────────────────────────────────────────────────

class UserMeResponse(BaseModel):
    """
    Response for GET /auth/me.
    Maps directly to the User ORM model (selected fields only).
    """
    id: str
    username: str
    email: str
    display_name: str
    category: str
    headline: str | None
    bio: str | None
    avatar_url: str | None
    is_verified: bool
    is_suspended: bool
    role: str
    show_online_status: bool
    allow_random_discovery: bool
    preferred_audience: str
    preferred_language: str
    default_matching_mode: str
    notify_connection_requests: bool
    notify_messages: bool

    model_config = {"from_attributes": True}
