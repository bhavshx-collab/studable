"""
Studable API — User ORM models.

Tables:
  users           — primary account record
  user_interests  — many-to-many interest tags per user
  user_skills     — many-to-many skill labels per user
  user_languages  — many-to-many language preferences per user
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ── users ─────────────────────────────────────────────────────────────────────

class User(Base):
    """
    Primary user account record.

    Keeps both authentication credentials and profile data in one table
    to minimise joins on the hot read path.  Soft-delete via deleted_at.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # ── Identity ──────────────────────────────────────────────────────────────
    username: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # ── Profile ───────────────────────────────────────────────────────────────
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    # Student | Working Professional | Entrepreneur | Mentor
    category: Mapped[str] = mapped_column(String(32), nullable=False, default="Student")
    headline: Mapped[str | None] = mapped_column(String(160), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ── Account state ─────────────────────────────────────────────────────────
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_suspended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # member | admin
    role: Mapped[str] = mapped_column(String(16), default="member", nullable=False)

    # ── Preferences ───────────────────────────────────────────────────────────
    show_online_status: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_random_discovery: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Students | Professionals | Anyone
    preferred_audience: Mapped[str] = mapped_column(String(16), default="Anyone", nullable=False)
    preferred_language: Mapped[str] = mapped_column(String(32), default="English", nullable=False)
    # random | interest
    default_matching_mode: Mapped[str] = mapped_column(String(16), default="interest", nullable=False)

    # ── Notification settings ─────────────────────────────────────────────────
    notify_connection_requests: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_messages: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    interests: Mapped[list[UserInterest]] = relationship(
        "UserInterest", back_populates="user", cascade="all, delete-orphan"
    )
    skills: Mapped[list[UserSkill]] = relationship(
        "UserSkill", back_populates="user", cascade="all, delete-orphan"
    )
    languages: Mapped[list[UserLanguage]] = relationship(
        "UserLanguage", back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(  # noqa: F821
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    sent_connections: Mapped[list["Connection"]] = relationship(  # noqa: F821
        "Connection", foreign_keys="Connection.requester_id",
        back_populates="requester", cascade="all, delete-orphan"
    )
    received_connections: Mapped[list["Connection"]] = relationship(  # noqa: F821
        "Connection", foreign_keys="Connection.recipient_id",
        back_populates="recipient", cascade="all, delete-orphan"
    )
    notifications: Mapped[list["Notification"]] = relationship(  # noqa: F821
        "Notification", foreign_keys="Notification.user_id",
        back_populates="user", cascade="all, delete-orphan"
    )
    blocks_given: Mapped[list["Block"]] = relationship(  # noqa: F821
        "Block", foreign_keys="Block.blocker_id",
        back_populates="blocker", cascade="all, delete-orphan"
    )
    blocks_received: Mapped[list["Block"]] = relationship(  # noqa: F821
        "Block", foreign_keys="Block.blocked_id",
        back_populates="blocked_user", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("role IN ('member', 'admin')", name="ck_users_role"),
        CheckConstraint(
            "category IN ('Student','Working Professional','Entrepreneur','Mentor')",
            name="ck_users_category",
        ),
        Index("ix_users_email", "email"),
        Index("ix_users_username", "username"),
        Index("ix_users_deleted_at", "deleted_at"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id!r} username={self.username!r}>"


# ── user_interests ────────────────────────────────────────────────────────────

class UserInterest(Base):
    """Interest tags attached to a user (e.g. 'Technology', 'Startups')."""

    __tablename__ = "user_interests"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    interest: Mapped[str] = mapped_column(String(64), primary_key=True)

    user: Mapped[User] = relationship("User", back_populates="interests")


# ── user_skills ───────────────────────────────────────────────────────────────

class UserSkill(Base):
    """Skill labels attached to a user (e.g. 'Python', 'Product Design')."""

    __tablename__ = "user_skills"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    skill: Mapped[str] = mapped_column(String(64), primary_key=True)

    user: Mapped[User] = relationship("User", back_populates="skills")


# ── user_languages ────────────────────────────────────────────────────────────

class UserLanguage(Base):
    """Language preferences attached to a user (e.g. 'English', 'Hindi')."""

    __tablename__ = "user_languages"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    language: Mapped[str] = mapped_column(String(32), primary_key=True)

    user: Mapped[User] = relationship("User", back_populates="languages")


# Avoid circular import — imported here after User is defined
from app.models.auth import RefreshToken          # noqa: E402, F401
from app.models.connection import Connection      # noqa: E402, F401
from app.models.notification import Notification  # noqa: E402, F401
from app.models.block import Block                # noqa: E402, F401
