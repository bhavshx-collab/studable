"""
Studable API — Notification ORM model.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Notification(Base):
    """
    In-app notification delivered to a specific user.

    related_entity_id is a generic UUID field (no FK) used to reference
    conversation IDs, connection IDs, etc., avoiding a large union-FK pattern.
    """

    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # connection_request | connection_accepted | new_message | account_update | moderation
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Generic: could point to a conversation, connection, etc.
    related_entity_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(  # noqa: F821
        "User", foreign_keys=[user_id], back_populates="notifications"
    )
    related_user: Mapped["User | None"] = relationship(  # noqa: F821
        "User", foreign_keys=[related_user_id]
    )

    __table_args__ = (
        # Hottest query: unread notifications for a user, newest first.
        Index("ix_notifications_user_read_created", "user_id", "is_read", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Notification id={self.id!r} type={self.type!r} is_read={self.is_read}>"
