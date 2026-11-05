"""developer_sessions

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-05 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. developer_sessions table
    op.create_table(
        "developer_sessions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("session_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column(
            "developer_id",
            sa.String(length=64),
            sa.ForeignKey("developers.developer_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("project_path", sa.String(length=512), nullable=True),
        sa.Column(
            "status", sa.String(length=32), nullable=False, server_default="active"
        ),
        sa.Column("started_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("last_activity_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("ended_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), nullable=False),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index(
        "ix_developer_sessions_session_id", "developer_sessions", ["session_id"]
    )
    op.create_index(
        "ix_developer_sessions_developer_id", "developer_sessions", ["developer_id"]
    )
    op.create_index("ix_developer_sessions_status", "developer_sessions", ["status"])
    op.create_index(
        "ix_developer_sessions_started_at", "developer_sessions", ["started_at"]
    )
    op.create_index(
        "ix_developer_sessions_last_activity_at",
        "developer_sessions",
        ["last_activity_at"],
    )
    op.create_index(
        "ix_dev_sessions_dev_status",
        "developer_sessions",
        ["developer_id", "status"],
    )
    op.create_index(
        "ix_dev_sessions_dev_started",
        "developer_sessions",
        ["developer_id", "started_at"],
    )

    # 2. Add session_id to developer_activities
    op.add_column(
        "developer_activities",
        sa.Column("session_id", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_dev_act_session_id", "developer_activities", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_dev_act_session_id", table_name="developer_activities")
    op.drop_column("developer_activities", "session_id")
    op.drop_table("developer_sessions")
