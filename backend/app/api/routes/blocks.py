"""
Studable API — Block/Unblock REST endpoints (Phase 7).

Endpoints:
  GET    /api/v1/blocks             – list users I've blocked
  POST   /api/v1/users/{id}/block   – block a user
  DELETE /api/v1/users/{id}/block   – unblock a user
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.block import Block
from app.models.user import User

router = APIRouter(tags=["Blocks"])


class BlockedUserOut(BaseModel):
    blocked_id: str
    blocked_at: str


@router.get("/blocks", summary="List blocked users")
def list_blocks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[BlockedUserOut]:
    rows = db.execute(
        select(Block).where(Block.blocker_id == current_user.id)
    ).scalars().all()
    return [BlockedUserOut(blocked_id=b.blocked_id, blocked_at=b.created_at.isoformat()) for b in rows]


@router.post("/users/{user_id}/block", status_code=status.HTTP_201_CREATED, summary="Block a user")
def block_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot block yourself")
    target = db.get(User, user_id)
    if target is None or target.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    existing = db.execute(
        select(Block).where(and_(Block.blocker_id == current_user.id, Block.blocked_id == user_id))
    ).scalar_one_or_none()
    if existing:
        return {"blocked": True, "already_blocked": True}

    block = Block(blocker_id=current_user.id, blocked_id=user_id)
    db.add(block)
    db.commit()
    return {"blocked": True}


@router.delete("/users/{user_id}/block", summary="Unblock a user")
def unblock_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    block = db.execute(
        select(Block).where(and_(Block.blocker_id == current_user.id, Block.blocked_id == user_id))
    ).scalar_one_or_none()
    if block is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found")
    db.delete(block)
    db.commit()
    return {"unblocked": True}
