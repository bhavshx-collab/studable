"""
Studable API — Report ORM model.

User-submitted content / conduct reports for moderation.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Report(Base):
    """
    Moderation report filed by one user against another.

    reporter_id and reported_user_id are SET NULL on user deletion so the
    report history survives for audit purposes.
    """

    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    reporter_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reported_user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    conversation_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    reason: Mapped[str] = mapped_column(String(128), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    # pending | resolved_warned | resolved_suspended | dismissed
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    moderator_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    reporter: Mapped["User | None"] = relationship("User", foreign_keys=[reporter_id])  # noqa: F821
    reported_user: Mapped["User | None"] = relationship("User", foreign_keys=[reported_user_id])  # noqa: F821
    moderator: Mapped["User | None"] = relationship("User", foreign_keys=[moderator_id])  # noqa: F821

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','resolved_warned','resolved_suspended','dismissed')",
            name="ck_reports_status",
        ),
        Index("ix_reports_status", "status"),
        Index("ix_reports_reporter_id", "reporter_id"),
        Index("ix_reports_reported_user_id", "reported_user_id"),
    )

    def __repr__(self) -> str:
        return f"<Report id={self.id!r} status={self.status!r}>"
