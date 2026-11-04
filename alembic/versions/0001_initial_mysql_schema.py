"""initial_mysql_schema

Revision ID: 0001
Revises:
Create Date: 2026-11-04 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. developers table
    op.create_table(
        "developers",
        sa.Column("developer_id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True, unique=True),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), nullable=False),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )

    # 2. skills table
    op.create_table(
        "skills",
        sa.Column("skill_id", sa.String(length=64), primary_key=True),
        sa.Column("skill_name", sa.String(length=128), nullable=False, unique=True),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_skills_category", "skills", ["category"])

    # 3. skill_relationships table
    op.create_table(
        "skill_relationships",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column(
            "from_skill_id",
            sa.String(length=64),
            sa.ForeignKey("skills.skill_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "to_skill_id",
            sa.String(length=64),
            sa.ForeignKey("skills.skill_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relationship_type", sa.String(length=32), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.UniqueConstraint(
            "from_skill_id",
            "to_skill_id",
            "relationship_type",
            name="uq_skill_rel_edge",
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_skill_rel_from", "skill_relationships", ["from_skill_id"])
    op.create_index("ix_skill_rel_to", "skill_relationships", ["to_skill_id"])

    # 4. developer_activities table
    op.create_table(
        "developer_activities",
        sa.Column("event_id", sa.String(length=64), primary_key=True),
        sa.Column(
            "developer_id",
            sa.String(length=64),
            sa.ForeignKey("developers.developer_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("project_path", sa.String(length=512), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("timestamp", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("file_path", sa.String(length=512), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index(
        "ix_dev_activities_event_type", "developer_activities", ["event_type"]
    )
    op.create_index(
        "ix_dev_activities_timestamp", "developer_activities", ["timestamp"]
    )
    op.create_index(
        "ix_dev_act_dev_time",
        "developer_activities",
        ["developer_id", "timestamp"],
    )

    # 5. skill_evidence table
    op.create_table(
        "skill_evidence",
        sa.Column("evidence_id", sa.String(length=64), primary_key=True),
        sa.Column(
            "developer_id",
            sa.String(length=64),
            sa.ForeignKey("developers.developer_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "skill_id",
            sa.String(length=64),
            sa.ForeignKey("skills.skill_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("evidence_type", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("timestamp", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("project_path", sa.String(length=512), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_skill_evidence_timestamp", "skill_evidence", ["timestamp"])
    op.create_index(
        "ix_skill_ev_lookup",
        "skill_evidence",
        ["developer_id", "skill_id"],
    )

    # 6. developer_skills table
    op.create_table(
        "developer_skills",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column(
            "developer_id",
            sa.String(length=64),
            sa.ForeignKey("developers.developer_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "skill_id",
            sa.String(length=64),
            sa.ForeignKey("skills.skill_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("proficiency_level", sa.String(length=32), nullable=False),
        sa.Column("evidence_count", sa.Integer(), nullable=False, default=0),
        sa.Column(
            "has_sufficient_evidence",
            sa.Boolean(),
            nullable=False,
            default=False,
        ),
        sa.Column("last_assessed", mysql.DATETIME(fsp=6), nullable=True),
        sa.UniqueConstraint("developer_id", "skill_id", name="uq_dev_skill_pair"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index(
        "ix_dev_skills_lookup",
        "developer_skills",
        ["developer_id", "skill_id"],
    )

    # 7. learning_progress table
    op.create_table(
        "learning_progress",
        sa.Column("progress_id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column(
            "developer_id",
            sa.String(length=64),
            sa.ForeignKey("developers.developer_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_goal_skill_id",
            sa.String(length=64),
            sa.ForeignKey("skills.skill_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("completion_percentage", sa.Float(), nullable=False, default=0.0),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.UniqueConstraint(
            "developer_id",
            "target_goal_skill_id",
            name="uq_learning_dev_goal",
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_learning_progress_dev", "learning_progress", ["developer_id"])

    # 8. learning_progress_items table
    op.create_table(
        "learning_progress_items",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column(
            "progress_id",
            sa.BigInteger(),
            sa.ForeignKey("learning_progress.progress_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "skill_id",
            sa.String(length=64),
            sa.ForeignKey("skills.skill_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("completed_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.UniqueConstraint(
            "progress_id", "skill_id", name="uq_learning_item_progress_skill"
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index(
        "ix_learning_item_status",
        "learning_progress_items",
        ["progress_id", "status"],
    )

    # 9. learning_progress_history table
    op.create_table(
        "learning_progress_history",
        sa.Column("history_id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column(
            "progress_id",
            sa.BigInteger(),
            sa.ForeignKey("learning_progress.progress_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "developer_id",
            sa.String(length=64),
            sa.ForeignKey("developers.developer_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_goal_skill_id",
            sa.String(length=64),
            sa.ForeignKey("skills.skill_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("completed_count", sa.Integer(), nullable=False),
        sa.Column("total_steps", sa.Integer(), nullable=False),
        sa.Column("completion_percentage", sa.Float(), nullable=False),
        sa.Column("change_summary", sa.String(length=255), nullable=True),
        sa.Column("recorded_at", mysql.DATETIME(fsp=6), nullable=False),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index(
        "ix_learning_progress_history_prog",
        "learning_progress_history",
        ["progress_id"],
    )
    op.create_index(
        "ix_learning_hist_dev_time",
        "learning_progress_history",
        ["developer_id", "recorded_at"],
    )


def downgrade() -> None:
    op.drop_table("learning_progress_history")
    op.drop_table("learning_progress_items")
    op.drop_table("learning_progress")
    op.drop_table("developer_skills")
    op.drop_table("skill_evidence")
    op.drop_table("developer_activities")
    op.drop_table("skill_relationships")
    op.drop_table("skills")
    op.drop_table("developers")
