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

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
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
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> None:
    """Verify the current password and update to a new one."""
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )
    user.password_hash = hash_password(payload.new_password)
    db.commit()


# ── POST /verify-email ────────────────────────────────────────────────────────

@router.post(
    "/verify-email",
    summary="[Stub] Verify email address with a token",
)
def verify_email(payload: VerifyEmailRequest) -> dict:
    """Email verification stub — SMTP integration required in a future phase."""
    return {
        "detail": (
            "Email verification is not yet configured. "
            "An email service integration will be added in a future phase."
        )
    }


# ── POST /resend-verification ─────────────────────────────────────────────────

@router.post(
    "/resend-verification",
    summary="[Stub] Resend verification email",
)
def resend_verification(payload: ResendVerificationRequest) -> dict:
    return {
        "detail": (
            "Resend verification is not yet configured. "
            "An email service integration will be added in a future phase."
        )
    }


# ── POST /forgot-password ─────────────────────────────────────────────────────

@router.post(
    "/forgot-password",
    summary="[Stub] Request a password reset email",
)
def forgot_password(payload: ForgotPasswordRequest) -> dict:
    """
    Always returns the same message to prevent email enumeration.
    SMTP integration will be added in a future phase.
    """
    return {
        "detail": (
            "If that email is registered, a reset link will be sent. "
            "(Email service integration coming in a future phase.)"
        )
    }


# ── POST /reset-password ──────────────────────────────────────────────────────

@router.post(
    "/reset-password",
    summary="[Stub] Reset password using a token",
)
def reset_password(payload: ResetPasswordRequest) -> dict:
    return {
        "detail": (
            "Password reset tokens are not yet implemented. "
            "An email service integration will be added in a future phase."
        )
    }
