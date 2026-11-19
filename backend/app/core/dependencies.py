"""
Studable API — FastAPI dependency injectors.

Provides reusable, composable dependencies for:
- Database session lifecycle.
- Current authenticated user (optional and required).
- Admin role gate.
"""

from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token

_bearer = HTTPBearer(auto_error=False)


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
    db: Session = Depends(get_db),
) -> "User | None":  # noqa: F821
    """
    Returns the authenticated User if a valid Bearer token is supplied,
    or None if no token is present.  Raises 401 only on a *bad* token.
    """
    from app.models.user import User

    if credentials is None:
        return None
    payload = decode_access_token(credentials.credentials)
    user_id: str = payload["sub"]
    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def get_current_user(
    user: "User | None" = Depends(get_current_user_optional),
) -> "User":
    """Require a fully authenticated, non-suspended user."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.is_suspended:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been suspended",
        )
    return user


def require_admin(
    user: "User" = Depends(get_current_user),
) -> "User":
    """Require the current user to have the 'admin' role."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )
    return user
