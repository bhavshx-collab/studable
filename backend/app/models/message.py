"""
Studable API — Message ORM model.

Individual chat messages within a Conversation.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Message(Base):
    """
    Single message in a Conversation.

    sender_id is SET NULL on user deletion so messages remain visible in
    conversation history (important for moderation review).
    """

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    conversation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # sent | delivered | read
    status: Mapped[str] = mapped_column(String(16), default="sent", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")  # noqa: F821

    __table_args__ = (
        CheckConstraint(
            "status IN ('sent', 'delivered', 'read')",
            name="ck_messages_status",
        ),
        # Hot-path index: fetch all messages in a conversation ordered by time.
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
        Index("ix_messages_sender_id", "sender_id"),
    )

    def __repr__(self) -> str:
        return f"<Message id={self.id!r} sender_id={self.sender_id!r}>"
