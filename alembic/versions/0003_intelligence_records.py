"""intelligence_and_adaptive_mentoring_records

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-06 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # 1. developer_insights
    if "developer_insights" not in existing_tables:
        op.create_table(
            "developer_insights",
            sa.Column("insight_id", sa.String(length=64), primary_key=True),
            sa.Column(
                "developer_id",
                sa.String(length=64),
                sa.ForeignKey("developers.developer_id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("category", sa.String(length=64), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.String(length=2048), nullable=False),
            sa.Column("severity", sa.String(length=32), nullable=False),
            sa.Column("evidence_json", sa.JSON(), nullable=False),
            sa.Column("supporting_skills_json", sa.JSON(), nullable=False),
            sa.Column(
                "actionable_recommendation", sa.String(length=1024), nullable=True
            ),
            sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
        )
        op.create_index(
            "ix_developer_insights_developer_id", "developer_insights", ["developer_id"]
        )
        op.create_index(
            "ix_developer_insights_category", "developer_insights", ["category"]
        )
        op.create_index(
            "ix_developer_insights_created_at", "developer_insights", ["created_at"]
        )
        op.create_index(
            "ix_dev_insight_dev_time",
            "developer_insights",
            ["developer_id", "created_at"],
        )

    # 2. developer_performance_snapshots
    if "developer_performance_snapshots" not in existing_tables:
        op.create_table(
            "developer_performance_snapshots",
            sa.Column("snapshot_id", sa.String(length=64), primary_key=True),
            sa.Column(
                "developer_id",
                sa.String(length=64),
                sa.ForeignKey("developers.developer_id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("timestamp", mysql.DATETIME(fsp=6), nullable=False),
            sa.Column(
                "total_activities", sa.Integer(), nullable=False, server_default="0"
            ),
            sa.Column(
                "verified_skills_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "average_proficiency_score",
                sa.Float(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "active_knowledge_gaps_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "tasks_completed_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "task_success_rate", sa.Float(), nullable=False, server_default="0"
            ),
            sa.Column(
                "learning_consistency_score",
                sa.Float(),
                nullable=False,
                server_default="0",
            ),
            sa.Column("role_readiness_json", sa.JSON(), nullable=False),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
        )
        op.create_index(
            "ix_developer_performance_snapshots_developer_id",
            "developer_performance_snapshots",
            ["developer_id"],
        )
        op.create_index(
            "ix_developer_performance_snapshots_timestamp",
            "developer_performance_snapshots",
            ["timestamp"],
        )
        op.create_index(
            "ix_dev_snapshot_dev_time",
            "developer_performance_snapshots",
            ["developer_id", "timestamp"],
        )

    # 3. personalized_tasks
    if "personalized_tasks" not in existing_tables:
        op.create_table(
            "personalized_tasks",
            sa.Column("task_id", sa.String(length=64), primary_key=True),
            sa.Column(
                "developer_id",
                sa.String(length=64),
                sa.ForeignKey("developers.developer_id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.String(length=2048), nullable=False),
            sa.Column("target_skill", sa.String(length=128), nullable=False),
            sa.Column("difficulty", sa.String(length=32), nullable=False),
            sa.Column("priority", sa.String(length=32), nullable=False),
            sa.Column(
                "status",
                sa.String(length=32),
                nullable=False,
                server_default="generated",
            ),
            sa.Column(
                "estimated_minutes", sa.Integer(), nullable=False, server_default="30"
            ),
            sa.Column("target_role", sa.String(length=128), nullable=True),
            sa.Column("prerequisite_skills_json", sa.JSON(), nullable=False),
            sa.Column("reason", sa.String(length=1024), nullable=False),
            sa.Column("acceptance_criteria_json", sa.JSON(), nullable=False),
            sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
            sa.Column("updated_at", mysql.DATETIME(fsp=6), nullable=False),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
        )
        op.create_index(
            "ix_personalized_tasks_developer_id", "personalized_tasks", ["developer_id"]
        )
        op.create_index(
            "ix_personalized_tasks_target_skill", "personalized_tasks", ["target_skill"]
        )
        op.create_index(
            "ix_personalized_tasks_status", "personalized_tasks", ["status"]
        )
        op.create_index(
            "ix_personalized_tasks_created_at", "personalized_tasks", ["created_at"]
        )
        op.create_index(
            "ix_dev_task_dev_status", "personalized_tasks", ["developer_id", "status"]
        )

    # 4. task_outcomes
    if "task_outcomes" not in existing_tables:
        op.create_table(
            "task_outcomes",
            sa.Column("outcome_id", sa.String(length=64), primary_key=True),
            sa.Column(
                "task_id",
                sa.String(length=64),
                sa.ForeignKey("personalized_tasks.task_id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "developer_id",
                sa.String(length=64),
                sa.ForeignKey("developers.developer_id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("success", sa.Boolean(), nullable=False),
            sa.Column("execution_notes", sa.String(length=2048), nullable=False),
            sa.Column("verified_artifacts_json", sa.JSON(), nullable=False),
            sa.Column("recorded_at", mysql.DATETIME(fsp=6), nullable=False),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
        )
        op.create_index("ix_task_outcomes_task_id", "task_outcomes", ["task_id"])
        op.create_index(
            "ix_task_outcomes_developer_id", "task_outcomes", ["developer_id"]
        )
        op.create_index(
            "ix_task_outcomes_recorded_at", "task_outcomes", ["recorded_at"]
        )
        op.create_index(
            "ix_task_outcomes_dev_time",
            "task_outcomes",
            ["developer_id", "recorded_at"],
        )
    else:
        task_outcomes_indexes = {
            idx["name"] for idx in inspector.get_indexes("task_outcomes")
        }
        if "ix_task_outcomes_dev_time" not in task_outcomes_indexes:
            op.create_index(
                "ix_task_outcomes_dev_time",
                "task_outcomes",
                ["developer_id", "recorded_at"],
            )

    # 5. developer_feedbacks
    if "developer_feedbacks" not in existing_tables:
        op.create_table(
            "developer_feedbacks",
            sa.Column("feedback_id", sa.String(length=64), primary_key=True),
            sa.Column(
                "developer_id",
                sa.String(length=64),
                sa.ForeignKey("developers.developer_id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("related_task_id", sa.String(length=64), nullable=True),
            sa.Column("related_skill", sa.String(length=128), nullable=True),
            sa.Column("category", sa.String(length=64), nullable=False),
            sa.Column("message", sa.String(length=2048), nullable=False),
            sa.Column("supporting_evidence_json", sa.JSON(), nullable=False),
            sa.Column(
                "recommended_next_action", sa.String(length=1024), nullable=False
            ),
            sa.Column(
                "confidence_level", sa.Float(), nullable=False, server_default="1.0"
            ),
            sa.Column("timestamp", mysql.DATETIME(fsp=6), nullable=False),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
        )
        op.create_index(
            "ix_developer_feedbacks_developer_id",
            "developer_feedbacks",
            ["developer_id"],
        )
        op.create_index(
            "ix_developer_feedbacks_timestamp", "developer_feedbacks", ["timestamp"]
        )
        op.create_index(
            "ix_dev_feedback_dev_time",
            "developer_feedbacks",
            ["developer_id", "timestamp"],
        )

    # 6. mentoring_sessions
    if "mentoring_sessions" not in existing_tables:
        op.create_table(
            "mentoring_sessions",
            sa.Column("session_id", sa.String(length=64), primary_key=True),
            sa.Column(
                "developer_id",
                sa.String(length=64),
                sa.ForeignKey("developers.developer_id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("strategy", sa.String(length=64), nullable=False),
            sa.Column("query", sa.String(length=2048), nullable=False),
            sa.Column("target_skill", sa.String(length=128), nullable=True),
            sa.Column("summary", sa.String(length=2048), nullable=False),
            sa.Column("outcome_rating", sa.Float(), nullable=True),
            sa.Column("outcome_notes", sa.String(length=1024), nullable=True),
            sa.Column("provider_used", sa.String(length=64), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=False),
            sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
        )
        op.create_index(
            "ix_mentoring_sessions_developer_id", "mentoring_sessions", ["developer_id"]
        )
        op.create_index(
            "ix_mentoring_sessions_created_at", "mentoring_sessions", ["created_at"]
        )
        op.create_index(
            "ix_mentoring_dev_time",
            "mentoring_sessions",
            ["developer_id", "created_at"],
        )
    else:
        existing_cols = {
            col["name"] for col in inspector.get_columns("mentoring_sessions")
        }
        if "provider_used" not in existing_cols:
            op.add_column(
                "mentoring_sessions",
                sa.Column("provider_used", sa.String(length=64), nullable=True),
            )
        if "metadata_json" not in existing_cols:
            op.add_column(
                "mentoring_sessions",
                sa.Column(
                    "metadata_json",
                    sa.JSON(),
                    nullable=True,
                ),
            )
            op.execute(
                sa.text(
                    "UPDATE mentoring_sessions SET metadata_json = JSON_OBJECT() WHERE metadata_json IS NULL"
                )
            )
            op.alter_column(
                "mentoring_sessions",
                "metadata_json",
                existing_type=sa.JSON(),
                nullable=False,
            )
        existing_indexes = {
            idx["name"] for idx in inspector.get_indexes("mentoring_sessions")
        }
        if "ix_mentoring_dev_time" not in existing_indexes:
            op.create_index(
                "ix_mentoring_dev_time",
                "mentoring_sessions",
                ["developer_id", "created_at"],
            )

    # 7. learning_adaptations
    if "learning_adaptations" not in existing_tables:
        op.create_table(
            "learning_adaptations",
            sa.Column("adaptation_id", sa.String(length=64), primary_key=True),
            sa.Column(
                "developer_id",
                sa.String(length=64),
                sa.ForeignKey("developers.developer_id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("previous_strategy", sa.String(length=64), nullable=False),
            sa.Column("new_strategy", sa.String(length=64), nullable=False),
            sa.Column("adaptation_reason", sa.String(length=1024), nullable=False),
            sa.Column("adjusted_difficulty", sa.String(length=32), nullable=False),
            sa.Column("adjusted_priorities_json", sa.JSON(), nullable=False),
            sa.Column("stalled_skills_json", sa.JSON(), nullable=False),
            sa.Column("timestamp", mysql.DATETIME(fsp=6), nullable=False),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
        )
        op.create_index(
            "ix_learning_adaptations_developer_id",
            "learning_adaptations",
            ["developer_id"],
        )
        op.create_index(
            "ix_learning_adaptations_timestamp",
            "learning_adaptations",
            ["timestamp"],
        )
        op.create_index(
            "ix_dev_adapt_dev_time",
            "learning_adaptations",
            ["developer_id", "timestamp"],
        )


def downgrade() -> None:
    op.drop_table("learning_adaptations")
    op.drop_table("mentoring_sessions")
    op.drop_table("developer_feedbacks")
    op.drop_table("task_outcomes")
    op.drop_table("personalized_tasks")
    op.drop_table("developer_performance_snapshots")
    op.drop_table("developer_insights")
