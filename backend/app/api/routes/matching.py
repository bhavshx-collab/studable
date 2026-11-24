"""
Studable API — Matching REST endpoints (Phase 5).

Endpoints:
  POST /api/v1/matching/join
  POST /api/v1/matching/cancel
  GET  /api/v1/matching/status
  POST /api/v1/matching/{match_id}/accept
  POST /api/v1/matching/{match_id}/reject
  GET  /api/v1/matching/history
"""

from __future__ import annotations

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from redis.asyncio import Redis
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.dependencies import get_current_user, get_db
from app.core.redis import get_redis
from app.models.match_request import MatchRequest
from app.models.user import User
from app.services.matching_service import (
    accept_match,
    cancel_queue,
    format_peer_summary,
    get_match_status,
    join_queue,
    reject_match,
)

router = APIRouter(prefix="/matching", tags=["Matching Engine"])


class JoinQueueRequest(BaseModel):
    mode: str = Field(
        ...,
        description="Matching mode: 'random' or 'interest'",
        pattern="^(random|interest)$",
    )


class MatchActionResponse(BaseModel):
    success: bool
    status: str
    message: str = ""
    data: Optional[dict[str, Any]] = None


@router.post("/join", response_model=MatchActionResponse, summary="Join matching queue")
async def join_matching_queue(
    body: JoinQueueRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> MatchActionResponse:
    """Enter the matching queue in 'random' or 'interest' mode."""
    ok, err, info = await join_queue(redis, db, current_user.id, body.mode)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err or "Could not join matching queue.",
        )
    return MatchActionResponse(
        success=True,
        status="QUEUED",
        message="Successfully queued for matching.",
        data=info,
    )


@router.post("/cancel", response_model=MatchActionResponse, summary="Leave matching queue")
async def cancel_matching_queue(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> MatchActionResponse:
    """Withdraw from the matching queue and revert presence to AVAILABLE."""
    ok, err = await cancel_queue(redis, db, current_user.id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err or "Failed to cancel matching.",
        )
    return MatchActionResponse(
        success=True,
        status="IDLE",
        message="Matching cancelled successfully.",
    )


@router.get("/status", summary="Get current matching status")
async def get_current_match_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict[str, Any]:
    """Retrieve current user queue or proposal state."""
    return await get_match_status(redis, db, current_user.id)


@router.post("/{match_id}/accept", response_model=MatchActionResponse, summary="Accept match proposal")
async def accept_match_proposal(
    match_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> MatchActionResponse:
    """Accept the active match proposal within the 30-second window."""
    ok, err, info = await accept_match(redis, db, current_user.id, match_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err or "Could not accept match proposal.",
        )
    return MatchActionResponse(
        success=True,
        status=info.get("status", "ACCEPTED"),
        message="Match proposal accepted.",
        data=info,
    )


@router.post("/{match_id}/reject", response_model=MatchActionResponse, summary="Decline match proposal")
async def reject_match_proposal(
    match_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> MatchActionResponse:
    """Decline a match proposal and reset presence to AVAILABLE."""
    ok, err = await reject_match(redis, db, current_user.id, match_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err or "Could not decline match proposal.",
        )
    return MatchActionResponse(
        success=True,
        status="REJECTED",
        message="Match proposal declined.",
    )


@router.get("/history", summary="Get matching history")
def get_matching_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve paginated match history for current user."""
    query = (
        select(MatchRequest)
        .options(
            joinedload(MatchRequest.user1),
            joinedload(MatchRequest.user2),
        )
        .where(
            or_(
                MatchRequest.user1_id == current_user.id,
                MatchRequest.user2_id == current_user.id,
            )
        )
        .order_by(MatchRequest.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    records = db.execute(query).unique().scalars().all()
    items = []
    for r in records:
        peer = r.user2 if r.user1_id == current_user.id else r.user1
        items.append({
            "id": r.id,
            "mode": r.mode,
            "status": r.status,
            "score": r.score,
            "peer": format_peer_summary(peer) if peer else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        })

    return {
        "items": items,
        "limit": limit,
        "offset": offset,
        "count": len(items),
    }
