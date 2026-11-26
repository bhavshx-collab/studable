"""
Studable API — User settings, privacy and account deletion endpoints (Phase 7).

Endpoints:
  PATCH  /api/v1/users/me/privacy    – update privacy settings
  DELETE /api/v1/users/me            – soft-delete own account
  POST   /api/v1/auth/forgot-password – request password reset token
  POST   /api/v1/auth/reset-password  – consume token, update password
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.core.redis import get_redis
from app.models.user import User
from app.services.auth_service import revoke_all_user_sessions
from redis.asyncio import Redis

router = APIRouter(tags=["User Settings"])

RESET_TOKEN_TTL = 900  # 15 minutes


# ── Schemas ──────────────────────────────────────────────────────────────────

class PrivacySettingsRequest(BaseModel):
    show_online_status: Optional[bool] = None
    allow_random_discovery: Optional[bool] = None


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


# ── Privacy ───────────────────────────────────────────────────────────────────

@router.patch("/users/me/privacy", summary="Update privacy settings")
def update_privacy(
    body: PrivacySettingsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if body.show_online_status is not None:
        current_user.show_online_status = body.show_online_status
    if body.allow_random_discovery is not None:
        current_user.allow_random_discovery = body.allow_random_discovery
    db.commit()
    return {
        "show_online_status": current_user.show_online_status,
        "allow_random_discovery": current_user.allow_random_discovery,
    }


# ── Account deletion (soft-delete) ────────────────────────────────────────────

@router.delete("/users/me", summary="Delete own account (soft-delete)")
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict:
    current_user.deleted_at = datetime.now(timezone.utc)
    # Anonymise PII
    current_user.email = f"deleted_{current_user.id}@deleted.invalid"
    current_user.username = f"deleted_{current_user.id[:8]}"
    current_user.password_hash = "DELETED"
    db.commit()
    await revoke_all_user_sessions(current_user.id, db, redis)
    return {"deleted": True}
