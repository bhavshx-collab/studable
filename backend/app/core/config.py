"""
Studable API — Centralized configuration.

All settings are loaded from environment variables (or a .env file).
No secrets are hardcoded here; defaults are safe for local development only.
"""

from __future__ import annotations

import json
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings loaded from environment variables."""

    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "Studable API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ── Database ─────────────────────────────────────────────────────────────
    # Uses psycopg3 (psycopg) driver.
    # Format: postgresql+psycopg://<user>:<password>@<host>:<port>/<dbname>
    DATABASE_URL: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/studable"
    )

    # ── CORS ─────────────────────────────────────────────────────────────────
    # Accepts either a JSON array string or a plain comma-separated list.
    # In production: set this to your real frontend origin only.
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> List[str]:
        """Accept JSON array or comma-separated string from env."""
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("["):
                return json.loads(value)
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value  # type: ignore[return-value]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# Singleton instance — import this everywhere.
settings = Settings()
