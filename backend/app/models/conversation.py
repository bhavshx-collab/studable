"""
Studable API — Conversation ORM model.

A Conversation is opened when two users are mutually matched and both accept.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Conversation(Base):
    """
    1-on-1 conversation between two matched users.

    participant_a / participant_b are SET NULL on user deletion so the
    conversation history is preserved for moderation purposes.
    """

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    participant_a: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    participant_b: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    topic: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # random | interest
    matching_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # active | ended
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    messages: Mapped[list["Message"]] = relationship(  # noqa: F821
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'ended')",
            name="ck_conversations_status",
        ),
        Index("ix_conversations_participant_a", "participant_a"),
        Index("ix_conversations_participant_b", "participant_b"),
        Index("ix_conversations_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<Conversation id={self.id!r} status={self.status!r}>"


from app.models.message import Message  # noqa: E402, F401
