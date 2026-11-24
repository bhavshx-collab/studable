"""
Studable API — MatchRequest ORM model.

Persists the lifecycle of every match proposal created by the matching engine.
Redis holds the ephemeral queue / reservation state; PostgreSQL holds the
durable record so history, analytics, and idempotency checks always work.

Match lifecycle
---------------
  IDLE        — initial state (not stored; requests start as QUEUED)
  QUEUED      — user is in the matching queue waiting for a partner
  MATCH_FOUND — a candidate pair has been proposed; both must accept
  ACCEPTED    — both users accepted; conversation can start
  REJECTED    — at least one user rejected the proposal
  CANCELLED   — user withdrew before a partner was found
  EXPIRED     — acceptance window closed without both accepting
  COMPLETED   — conversation ended normally
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MatchRequest(Base):
    """
    Persistent record of one matching lifecycle.

    One row is created when a user joins the queue (status=QUEUED).
    When a partner is found user2_id is populated and status moves to MATCH_FOUND.
    """

    __tablename__ = "match_requests"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # ── Participants ───────────────────────────────────────────────────────────
    user1_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    user2_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Match parameters ───────────────────────────────────────────────────────
    # random | interest
    mode: Mapped[str] = mapped_column(String(16), nullable=False)

    # QUEUED | MATCH_FOUND | ACCEPTED | REJECTED | CANCELLED | EXPIRED | COMPLETED
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="QUEUED")

    # Interest-based compatibility score (null for random mode)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Acceptance tracking ────────────────────────────────────────────────────
    user1_accepted: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    user2_accepted: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # ── Timestamps ─────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Deadline by which both users must accept (set when MATCH_FOUND)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    user1: Mapped["User"] = relationship(  # noqa: F821
        "User", foreign_keys=[user1_id]
    )
    user2: Mapped["User | None"] = relationship(  # noqa: F821
        "User", foreign_keys=[user2_id]
    )

    __table_args__ = (
        CheckConstraint(
            "mode IN ('random','interest')",
            name="ck_match_requests_mode",
        ),
        CheckConstraint(
            "status IN ('QUEUED','MATCH_FOUND','ACCEPTED','REJECTED','CANCELLED','EXPIRED','COMPLETED')",
            name="ck_match_requests_status",
        ),
        Index("ix_match_requests_user1_id", "user1_id"),
        Index("ix_match_requests_user2_id", "user2_id"),
        Index("ix_match_requests_status", "status"),
        Index("ix_match_requests_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<MatchRequest id={self.id!r} status={self.status!r} "
            f"mode={self.mode!r} user1={self.user1_id!r} user2={self.user2_id!r}>"
        )
