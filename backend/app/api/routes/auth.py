"""
Studable API — Authentication routes.

POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
POST   /api/v1/auth/logout
GET    /api/v1/auth/me
POST   /api/v1/auth/change-password
POST   /api/v1/auth/verify-email         (stub)
POST   /api/v1/auth/resend-verification  (stub)
POST   /api/v1/auth/forgot-password      (stub)
POST   /api/v1/auth/reset-password       (stub)
"""

from __future__ import annotations

import logging
import secrets
from redis.asyncio import Redis
from app.core.redis import get_redis

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.core.security import (
    clear_refresh_cookie,
    get_refresh_token_from_cookie,
    hash_password,
    set_refresh_cookie,
    verify_password,
)
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    ResendVerificationRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserMeResponse,
    VerifyEmailRequest,
)
from app.services.auth_service import (
    login_user,
    logout_user,
    refresh_access_token,
    register_user,
    revoke_all_user_sessions,
)
from app.services.email_service import (
    send_password_reset_email,
    send_verification_email,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── POST /register ────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Studable account",
)
def register(
    payload: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> RegisterResponse:
    """
    Create a new user account.
    Sets an HttpOnly refresh token cookie and returns the user record.
    The access token is provided in the X-Access-Token response header.
    """
    user, raw_access, raw_refresh = register_user(payload, db)
    set_refresh_cookie(response, raw_refresh)
    response.headers["X-Access-Token"] = raw_access
    return RegisterResponse.model_validate(user)


# ── POST /login ───────────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with email and password",
)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Validate credentials and issue a JWT access token + HttpOnly refresh cookie.
    """
    _user, raw_access, raw_refresh = login_user(payload, db)
    set_refresh_cookie(response, raw_refresh)
    return TokenResponse(access_token=raw_access)


# ── POST /refresh ─────────────────────────────────────────────────────────────

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate refresh token and issue new access token",
)
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Accepts the refresh token from an HttpOnly cookie.
    Revokes the old token and issues a new pair (rotation).
    """
    raw_refresh = get_refresh_token_from_cookie(request)
    if not raw_refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token provided.",
        )
    _user, raw_access, raw_new_refresh = refresh_access_token(raw_refresh, db)
    set_refresh_cookie(response, raw_new_refresh)
    return TokenResponse(access_token=raw_access)


# ── POST /logout ──────────────────────────────────────────────────────────────

@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Logout and revoke refresh token",
)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> None:
    """
    Revoke the current refresh token and clear the cookie.
    Always returns 204 regardless of token state (prevents enumeration).
    """
    raw_refresh = get_refresh_token_from_cookie(request)
    logout_user(raw_refresh, db)
    clear_refresh_cookie(response)


# ── GET /me ───────────────────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=UserMeResponse,
    summary="Get current authenticated user profile",
)
def me(user=Depends(get_current_user)) -> UserMeResponse:
    """Return the full profile of the currently authenticated user."""
    return UserMeResponse.model_validate(user)


# ── POST /change-password ─────────────────────────────────────────────────────

@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Change your password",
)
async def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    redis: Redis = Depends(get_redis),
) -> None:
    """Verify the current password and update to a new one, revoking old sessions."""
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    await revoke_all_user_sessions(user.id, db, redis)


# ── POST /logout-all ──────────────────────────────────────────────────────────

@router.post(
    "/logout-all",
    summary="Log out of all devices and active sessions",
)
async def logout_all(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict:
    count = await revoke_all_user_sessions(current_user.id, db, redis)
    clear_refresh_cookie(response)
    return {"revoked_sessions": count}


# ── POST /verify-email ────────────────────────────────────────────────────────

@router.post(
    "/verify-email",
    summary="Verify email address with a token",
)
async def verify_email(
    payload: VerifyEmailRequest,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict:
    key = f"email_verify:{payload.token}"
    try:
        user_id = await redis.get(key)
    except Exception:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Cache unavailable")

    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification token")

    if isinstance(user_id, bytes):
        user_id = user_id.decode("utf-8")

    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found")

    user.is_verified = True
    db.commit()
    try:
        await redis.delete(key)
    except Exception:
        pass

    return {"detail": "Email verified successfully"}


# ── POST /resend-verification ─────────────────────────────────────────────────

@router.post(
    "/resend-verification",
    summary="Resend verification email",
)
async def resend_verification(
    payload: ResendVerificationRequest,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict:
    user = db.execute(
        select(User).where(User.email == payload.email, User.deleted_at.is_(None))
    ).scalar_one_or_none()

    if user is None:
        return {"detail": "If that email is registered, a verification link has been sent."}

    if user.is_verified:
        return {"detail": "Email is already verified."}

    token = secrets.token_urlsafe(32)
    key = f"email_verify:{token}"
    try:
        await redis.set(key, user.id, ex=86400)
    except Exception:
        pass

    await send_verification_email(user.email, token)

    return {
        "detail": "If that email is registered, a verification link has been sent.",
        "dev_token": token,
    }


# ── POST /forgot-password ─────────────────────────────────────────────────────

@router.post(
    "/forgot-password",
    summary="Request a password reset email",
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict:
    user = db.execute(
        select(User).where(User.email == payload.email, User.deleted_at.is_(None))
    ).scalar_one_or_none()

    # Always return 200 to prevent user enumeration
    if user is None:
        return {"detail": "If that email exists, a reset link has been sent."}

    token = secrets.token_urlsafe(32)
    key = f"pw_reset:{token}"
    try:
        await redis.set(key, user.id, ex=900)
    except Exception:
        pass

    await send_password_reset_email(user.email, token)

    return {
        "detail": "If that email exists, a reset link has been sent.",
        "dev_token": token,
    }


# ── POST /reset-password ──────────────────────────────────────────────────────

@router.post(
    "/reset-password",
    summary="Reset password using a token",
)
async def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict:
    key = f"pw_reset:{payload.token}"
    try:
        user_id = await redis.get(key)
    except Exception:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Cache unavailable")

    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    if isinstance(user_id, bytes):
        user_id = user_id.decode("utf-8")

    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found")

    user.password_hash = hash_password(payload.new_password)
    db.commit()
    try:
        await redis.delete(key)
    except Exception:
        pass

    await revoke_all_user_sessions(user.id, db, redis)

    return {"detail": "Password updated successfully"}
