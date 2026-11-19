"""
Studable API — Connection ORM model.

A Connection represents a pending or accepted relationship between two users.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Connection(Base):
    """
    Peer connection between requester and recipient.

    Status lifecycle: pending → accepted | rejected
    """

    __tablename__ = "connections"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    requester_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    recipient_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # pending | accepted | rejected
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    shared_topic: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    requester: Mapped["User"] = relationship(  # noqa: F821
        "User", foreign_keys=[requester_id], back_populates="sent_connections"
    )
    recipient: Mapped["User"] = relationship(  # noqa: F821
        "User", foreign_keys=[recipient_id], back_populates="received_connections"
    )

    __table_args__ = (
        UniqueConstraint("requester_id", "recipient_id", name="uq_connections_pair"),
        CheckConstraint("requester_id <> recipient_id", name="ck_connections_no_self"),
        CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected')",
            name="ck_connections_status",
        ),
        Index("ix_connections_requester_id", "requester_id"),
        Index("ix_connections_recipient_id", "recipient_id"),
        Index("ix_connections_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<Connection id={self.id!r} status={self.status!r}>"
