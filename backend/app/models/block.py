"""
Studable API — Block ORM model.

Bi-directional block: blocker → blocked_user.
Both FK sides CASCADE-delete on user removal.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Block(Base):
    """
    Block record: a user (blocker) has blocked another user (blocked_user).

    Composite primary key ensures uniqueness. The CHECK constraint prevents
    self-blocking at the database level.
    """

    __tablename__ = "blocks"

    blocker_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    blocked_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    blocker: Mapped["User"] = relationship(  # noqa: F821
        "User", foreign_keys=[blocker_id], back_populates="blocks_given"
    )
    blocked_user: Mapped["User"] = relationship(  # noqa: F821
        "User", foreign_keys=[blocked_id], back_populates="blocks_received"
    )

    __table_args__ = (
        CheckConstraint("blocker_id <> blocked_id", name="ck_blocks_no_self"),
    )

    def __repr__(self) -> str:
        return f"<Block blocker={self.blocker_id!r} blocked={self.blocked_id!r}>"
