"""Add match_requests table for real-time matching engine.

Revision ID: 0002_add_match_requests
Revises: 0001_initial_schema
Create Date: 2026-11-24 14:00:00

Tables created:
  - match_requests
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_add_match_requests"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "match_requests",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "user1_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user2_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="QUEUED"),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("user1_accepted", sa.Boolean(), nullable=True),
        sa.Column("user2_accepted", sa.Boolean(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "mode IN ('random','interest')",
            name="ck_match_requests_mode",
        ),
        sa.CheckConstraint(
            "status IN ('QUEUED','MATCH_FOUND','ACCEPTED','REJECTED','CANCELLED','EXPIRED','COMPLETED')",
            name="ck_match_requests_status",
        ),
    )
    op.create_index("ix_match_requests_user1_id", "match_requests", ["user1_id"])
    op.create_index("ix_match_requests_user2_id", "match_requests", ["user2_id"])
    op.create_index("ix_match_requests_status", "match_requests", ["status"])
    op.create_index("ix_match_requests_created_at", "match_requests", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_match_requests_created_at", table_name="match_requests")
    op.drop_index("ix_match_requests_status", table_name="match_requests")
    op.drop_index("ix_match_requests_user2_id", table_name="match_requests")
    op.drop_index("ix_match_requests_user1_id", table_name="match_requests")
    op.drop_table("match_requests")
