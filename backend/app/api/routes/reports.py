"""
Studable API — Report REST endpoints (Phase 7).

Endpoints:
  POST /api/v1/users/{id}/report   – submit a report
  GET  /api/v1/reports/mine        – reports I filed (audit)
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.report import Report
from app.models.user import User

router = APIRouter(tags=["Reports"])

VALID_REASONS = {
    "Spam",
    "Harassment",
    "Inappropriate content",
    "Hate speech",
    "Impersonation",
    "Other",
}


class ReportRequest(BaseModel):
    reason: str = Field(..., min_length=2, max_length=128)
    details: Optional[str] = Field(None, max_length=1000)
    conversation_id: Optional[str] = None


class ReportOut(BaseModel):
    id: str
    reported_user_id: Optional[str]
    reason: str
    status: str
    created_at: str


@router.post("/users/{user_id}/report", status_code=status.HTTP_201_CREATED, summary="Report a user")
def report_user(
    user_id: str,
    body: ReportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportOut:
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot report yourself")
    target = db.get(User, user_id)
    if target is None or target.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    report = Report(
        id=str(uuid.uuid4()),
        reporter_id=current_user.id,
        reported_user_id=user_id,
        conversation_id=body.conversation_id,
        reason=body.reason,
        details=body.details,
        status="pending",
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return ReportOut(
        id=report.id,
        reported_user_id=report.reported_user_id,
        reason=report.reason,
        status=report.status,
        created_at=report.created_at.isoformat(),
    )
