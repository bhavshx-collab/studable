"""
Studable API — Admin REST endpoints (Phase 7).

All routes require admin role (via require_admin dependency).

Endpoints:
  GET  /api/v1/admin/reports              – list reports (paginated)
  POST /api/v1/admin/reports/{id}/resolve – resolve a report
  GET  /api/v1/admin/users                – list users (search)
  POST /api/v1/admin/users/{id}/suspend   – suspend a user
  DELETE /api/v1/admin/users/{id}/suspend – unsuspend a user
  GET  /api/v1/admin/metrics              – platform stats
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_admin
from app.core.redis import get_redis
from app.services.auth_service import revoke_all_user_sessions
from redis.asyncio import Redis
from app.models.conversation import Conversation
from app.models.match_request import MatchRequest
from app.models.report import Report
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["Admin"])

VALID_RESOLVE_ACTIONS = {"resolved_warned", "resolved_suspended", "dismissed"}


# ── Schemas ──────────────────────────────────────────────────────────────────

class ReportAdminOut(BaseModel):
    id: str
    reporter_id: Optional[str]
    reported_user_id: Optional[str]
    reason: str
    details: Optional[str]
    status: str
    moderator_id: Optional[str]
    resolved_at: Optional[str]
    created_at: str


class ResolveReportRequest(BaseModel):
    action: str  # resolved_warned | resolved_suspended | dismissed


class UserAdminOut(BaseModel):
    id: str
    username: str
    display_name: str
    email: str
    role: str
    is_suspended: bool
    is_verified: bool
    created_at: str


# ── Report management ─────────────────────────────────────────────────────────

@router.get("/reports", summary="List reports")
def list_reports(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    report_status: Optional[str] = Query(None, alias="status"),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> List[ReportAdminOut]:
    q = select(Report)
    if report_status:
        q = q.where(Report.status == report_status)
    q = q.order_by(Report.created_at.desc()).offset((page - 1) * limit).limit(limit)
    rows = db.execute(q).scalars().all()
    return [
        ReportAdminOut(
            id=r.id,
            reporter_id=r.reporter_id,
            reported_user_id=r.reported_user_id,
            reason=r.reason,
            details=r.details,
            status=r.status,
            moderator_id=r.moderator_id,
            resolved_at=r.resolved_at.isoformat() if r.resolved_at else None,
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]


@router.post("/reports/{report_id}/resolve", summary="Resolve a report")
async def resolve_report(
    report_id: str,
    body: ResolveReportRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict:
    if body.action not in VALID_RESOLVE_ACTIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action. Must be one of: {VALID_RESOLVE_ACTIONS}",
        )
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    if report.status != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Report already resolved")

    report.status = body.action
    report.moderator_id = admin.id
    report.resolved_at = datetime.now(timezone.utc)

    # Auto-suspend and revoke sessions on resolved_suspended
    if body.action == "resolved_suspended" and report.reported_user_id:
        target = db.get(User, report.reported_user_id)
        if target:
            target.is_suspended = True
            await revoke_all_user_sessions(report.reported_user_id, db, redis)

    db.commit()
    return {"resolved": True, "action": body.action}


# ── User management ───────────────────────────────────────────────────────────

@router.get("/users", summary="List users")
def list_users(
    q: Optional[str] = Query(None, description="Search by username or email"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> List[UserAdminOut]:
    query = select(User).where(User.deleted_at.is_(None))
    if q:
        like = f"%{q}%"
        query = query.where(or_(User.username.ilike(like), User.email.ilike(like)))
    query = query.order_by(User.created_at.desc()).offset((page - 1) * limit).limit(limit)
    users = db.execute(query).scalars().all()
    return [
        UserAdminOut(
            id=u.id,
            username=u.username,
            display_name=u.display_name,
            email=u.email,
            role=u.role,
            is_suspended=u.is_suspended,
            is_verified=u.is_verified,
            created_at=u.created_at.isoformat(),
        )
        for u in users
    ]


@router.post("/users/{user_id}/suspend", summary="Suspend a user")
async def suspend_user(
    user_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict:
    target = db.get(User, user_id)
    if target is None or target.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if target.id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot suspend yourself")
    target.is_suspended = True
    db.commit()
    await revoke_all_user_sessions(user_id, db, redis)
    return {"suspended": True}


@router.delete("/users/{user_id}/suspend", summary="Unsuspend a user")
def unsuspend_user(
    user_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    target = db.get(User, user_id)
    if target is None or target.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    target.is_suspended = False
    db.commit()
    return {"unsuspended": True}


# ── Metrics ────────────────────────────────────────────────────────────────────

@router.get("/metrics", summary="Platform metrics")
def platform_metrics(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    total_users = db.execute(select(func.count()).select_from(User).where(User.deleted_at.is_(None))).scalar_one()
    suspended_users = db.execute(select(func.count()).select_from(User).where(User.is_suspended.is_(True))).scalar_one()
    total_conversations = db.execute(select(func.count()).select_from(Conversation)).scalar_one()
    pending_reports = db.execute(select(func.count()).select_from(Report).where(Report.status == "pending")).scalar_one()
    total_matches = db.execute(select(func.count()).select_from(MatchRequest)).scalar_one()

    return {
        "total_users": total_users,
        "suspended_users": suspended_users,
        "total_conversations": total_conversations,
        "pending_reports": pending_reports,
        "total_matches": total_matches,
    }
