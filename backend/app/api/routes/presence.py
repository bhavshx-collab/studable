"""
Studable API — Presence REST endpoints.

GET  /api/v1/presence/me            Current user's presence state
PATCH /api/v1/presence/me           Update own presence (AVAILABLE | BUSY only)
GET  /api/v1/presence/users/{uid}   Another user's presence state
GET  /api/v1/presence/available     Paginated list of AVAILABLE users
GET  /api/v1/presence/online        Online user count (used by ConnectLobbyPage)
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from redis.asyncio import Redis

from app.core.dependencies import get_current_user
from app.core.redis import get_redis
from app.models.user import User
from app.services.presence_service import (
    PresenceStatus,
    get_available_users,
    get_online_count,
    get_online_users,
    get_presence,
    set_presence_validated,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/presence", tags=["Presence"])


# ── Schemas ───────────────────────────────────────────────────────────────────


class PresenceResponse(BaseModel):
    user_id: str
    status: str


class PatchPresenceRequest(BaseModel):
    status: str


class OnlineCountResponse(BaseModel):
    online_count: int


class AvailableUsersResponse(BaseModel):
    user_ids: List[str]
    total: int


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get(
    "/me",
    response_model=PresenceResponse,
    summary="Get my presence status",
    description="Return the current authenticated user's presence state.",
)
async def get_my_presence(
    current_user: User = Depends(get_current_user),
    redis: Redis = Depends(get_redis),
) -> PresenceResponse:
    state = await get_presence(redis, str(current_user.id))
    return PresenceResponse(user_id=str(current_user.id), status=state.value)


@router.patch(
    "/me",
    response_model=PresenceResponse,
    summary="Update my presence status",
    description=(
        "Update your presence to AVAILABLE or BUSY. "
        "MATCHING and IN_CONVERSATION can only be set by backend operations."
    ),
)
async def patch_my_presence(
    body: PatchPresenceRequest,
    current_user: User = Depends(get_current_user),
    redis: Redis = Depends(get_redis),
) -> PresenceResponse:
    try:
        new_status = PresenceStatus(body.status.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status '{body.status}'. "
                   f"Allowed: AVAILABLE, BUSY.",
        )

    success, error_msg = await set_presence_validated(
        redis,
        str(current_user.id),
        new_status,
        allow_backend_only=False,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error_msg,
        )

    return PresenceResponse(user_id=str(current_user.id), status=new_status.value)


@router.get(
    "/users/{user_id}",
    response_model=PresenceResponse,
    summary="Get another user's presence",
    description=(
        "Return the presence state of a specific user. "
        "In Phase 4 all online/offline states are publicly visible to authenticated users. "
        "Phase 5 will add privacy controls."
    ),
)
async def get_user_presence(
    user_id: str,
    current_user: User = Depends(get_current_user),
    redis: Redis = Depends(get_redis),
) -> PresenceResponse:
    state = await get_presence(redis, user_id)
    return PresenceResponse(user_id=user_id, status=state.value)


@router.get(
    "/available",
    response_model=AvailableUsersResponse,
    summary="List available users",
    description="Return a paginated list of user IDs currently in AVAILABLE state.",
)
async def list_available_users(
    limit: int = Query(default=50, ge=1, le=200, description="Maximum users to return"),
    current_user: User = Depends(get_current_user),
    redis: Redis = Depends(get_redis),
) -> AvailableUsersResponse:
    user_ids = await get_available_users(redis, limit=limit)
    return AvailableUsersResponse(user_ids=user_ids, total=len(user_ids))


@router.get(
    "/online",
    response_model=OnlineCountResponse,
    summary="Get online user count",
    description=(
        "Return the number of users currently online (non-OFFLINE). "
        "Used by ConnectLobbyPage to display the live online count."
    ),
)
async def get_online_user_count(
    current_user: User = Depends(get_current_user),
    redis: Redis = Depends(get_redis),
) -> OnlineCountResponse:
    count = await get_online_count(redis)
    return OnlineCountResponse(online_count=count)
