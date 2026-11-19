"""
Studable API — Centralized configuration.

All settings are loaded from environment variables (or a .env file).
No secrets are hardcoded here; defaults are safe for local development only.
"""

from __future__ import annotations

import json
import secrets
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings loaded from environment variables."""

    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "Studable API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development | staging | production

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/studable"
    )

    # ── CORS ─────────────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    # ── JWT ───────────────────────────────────────────────────────────────────
    # In production, set JWT_SECRET_KEY to a securely generated 32-byte hex string.
    # e.g.: python -c "import secrets; print(secrets.token_hex(32))"
    JWT_SECRET_KEY: str = ""   # Must be overridden in production via env
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── Cookies ───────────────────────────────────────────────────────────────
    REFRESH_COOKIE_NAME: str = "studable_refresh"
    REFRESH_COOKIE_SECURE: bool = False   # Set True in production (HTTPS only)
    REFRESH_COOKIE_SAMESITE: str = "strict"

    # ── Admin ─────────────────────────────────────────────────────────────────
    ADMIN_EMAIL: str = "admin@studable.app"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> List[str]:
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("["):
                return json.loads(value)
            return [o.strip() for o in value.split(",") if o.strip()]
        return value  # type: ignore[return-value]

    @field_validator("JWT_SECRET_KEY", mode="before")
    @classmethod
    def ensure_jwt_secret(cls, value: str) -> str:
        """In development, auto-generate a temporary secret if not set."""
        if not value:
            return secrets.token_hex(32)
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# Singleton instance — import this everywhere.
settings = Settings()
