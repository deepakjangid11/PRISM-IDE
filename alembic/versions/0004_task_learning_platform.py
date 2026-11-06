"""task_learning_platform_schema

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-06 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # 1. Update developers table with authentication fields
    if "developers" in existing_tables:
        dev_cols = {col["name"] for col in inspector.get_columns("developers")}
        if "password_hash" not in dev_cols:
            op.add_column(
                "developers",
                sa.Column("password_hash", sa.String(length=255), nullable=True),
            )
        if "role" not in dev_cols:
            op.add_column(
                "developers",
                sa.Column(
                    "role",
                    sa.String(length=32),
                    nullable=False,
                    server_default="developer",
                ),
            )
        if "is_active" not in dev_cols:
            op.add_column(
                "developers",
                sa.Column(
                    "is_active",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.true(),
                ),
            )

    # 2. Update personalized_tasks table with rich task generation attributes
    if "personalized_tasks" in existing_tables:
        task_cols = {col["name"] for col in inspector.get_columns("personalized_tasks")}
        if "problem_statement" not in task_cols:
            op.add_column(
                "personalized_tasks",
                sa.Column("problem_statement", sa.Text(), nullable=True),
            )
        if "learning_objectives_json" not in task_cols:
            op.add_column(
                "personalized_tasks",
                sa.Column("learning_objectives_json", sa.JSON(), nullable=True),
            )
        if "requirements_json" not in task_cols:
            op.add_column(
                "personalized_tasks",
                sa.Column("requirements_json", sa.JSON(), nullable=True),
            )
        if "test_cases_json" not in task_cols:
            op.add_column(
                "personalized_tasks",
                sa.Column("test_cases_json", sa.JSON(), nullable=True),
            )
        if "hints_json" not in task_cols:
            op.add_column(
                "personalized_tasks",
                sa.Column("hints_json", sa.JSON(), nullable=True),
            )
        if "expected_deliverables_json" not in task_cols:
            op.add_column(
                "personalized_tasks",
                sa.Column("expected_deliverables_json", sa.JSON(), nullable=True),
            )
        if "evaluation_criteria_json" not in task_cols:
            op.add_column(
                "personalized_tasks",
                sa.Column("evaluation_criteria_json", sa.JSON(), nullable=True),
            )

    # 3. Create task_submissions table
    if "task_submissions" not in existing_tables:
        op.create_table(
            "task_submissions",
            sa.Column("submission_id", sa.String(length=64), primary_key=True),
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
            sa.Column(
                "submission_type",
                sa.String(length=32),
                nullable=False,
                server_default="code",
            ),
            sa.Column("source_code", sa.Text(), nullable=True),
            sa.Column("file_tree_json", sa.JSON(), nullable=False),
            sa.Column("repo_url", sa.String(length=512), nullable=True),
            sa.Column("explanation", sa.Text(), nullable=True),
            sa.Column(
                "status",
                sa.String(length=32),
                nullable=False,
                server_default="submitted",
            ),
            sa.Column("submitted_at", mysql.DATETIME(fsp=6), nullable=False),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
        )
        op.create_index("ix_task_submissions_task_id", "task_submissions", ["task_id"])
        op.create_index(
            "ix_task_submissions_developer_id",
            "task_submissions",
            ["developer_id"],
        )
        op.create_index(
            "ix_task_submissions_submitted_at",
            "task_submissions",
            ["submitted_at"],
        )
        op.create_index(
            "ix_submissions_dev_time",
            "task_submissions",
            ["developer_id", "submitted_at"],
        )

    # 4. Create task_evaluations table
    if "task_evaluations" not in existing_tables:
        op.create_table(
            "task_evaluations",
            sa.Column("evaluation_id", sa.String(length=64), primary_key=True),
            sa.Column(
                "submission_id",
                sa.String(length=64),
                sa.ForeignKey("task_submissions.submission_id", ondelete="CASCADE"),
                nullable=False,
            ),
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
            sa.Column("passed", sa.Boolean(), nullable=False),
            sa.Column("score", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column(
                "completion_status",
                sa.String(length=32),
                nullable=False,
                server_default="needs_revision",
            ),
            sa.Column("strengths_json", sa.JSON(), nullable=False),
            sa.Column("mistakes_json", sa.JSON(), nullable=False),
            sa.Column("missing_requirements_json", sa.JSON(), nullable=False),
            sa.Column("improvement_suggestions_json", sa.JSON(), nullable=False),
            sa.Column("recommended_next_steps_json", sa.JSON(), nullable=False),
            sa.Column("test_results_json", sa.JSON(), nullable=False),
            sa.Column("feedback_message", sa.Text(), nullable=False),
            sa.Column("generated_evidence_id", sa.String(length=64), nullable=True),
            sa.Column("evaluated_at", mysql.DATETIME(fsp=6), nullable=False),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
        )
        op.create_index(
            "ix_task_evaluations_submission_id",
            "task_evaluations",
            ["submission_id"],
        )
        op.create_index("ix_task_evaluations_task_id", "task_evaluations", ["task_id"])
        op.create_index(
            "ix_task_evaluations_developer_id",
            "task_evaluations",
            ["developer_id"],
        )
        op.create_index(
            "ix_task_evaluations_evaluated_at",
            "task_evaluations",
            ["evaluated_at"],
        )
        op.create_index(
            "ix_evaluations_dev_time",
            "task_evaluations",
            ["developer_id", "evaluated_at"],
        )

    # 5. Create mentoring_conversations table
    if "mentoring_conversations" not in existing_tables:
        op.create_table(
            "mentoring_conversations",
            sa.Column("conversation_id", sa.String(length=64), primary_key=True),
            sa.Column(
                "task_id",
                sa.String(length=64),
                sa.ForeignKey("personalized_tasks.task_id", ondelete="CASCADE"),
                nullable=True,
            ),
            sa.Column(
                "developer_id",
                sa.String(length=64),
                sa.ForeignKey("developers.developer_id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column(
                "current_guidance_level",
                sa.Integer(),
                nullable=False,
                server_default="1",
            ),
            sa.Column(
                "status",
                sa.String(length=32),
                nullable=False,
                server_default="active",
            ),
            sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
            sa.Column("updated_at", mysql.DATETIME(fsp=6), nullable=False),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
        )
        op.create_index(
            "ix_mentoring_conv_task_id",
            "mentoring_conversations",
            ["task_id"],
        )
        op.create_index(
            "ix_mentoring_conv_developer_id",
            "mentoring_conversations",
            ["developer_id"],
        )
        op.create_index(
            "ix_mentor_conv_dev_time",
            "mentoring_conversations",
            ["developer_id", "updated_at"],
        )

    # 6. Create mentoring_messages table
    if "mentoring_messages" not in existing_tables:
        op.create_table(
            "mentoring_messages",
            sa.Column("message_id", sa.String(length=64), primary_key=True),
            sa.Column(
                "conversation_id",
                sa.String(length=64),
                sa.ForeignKey(
                    "mentoring_conversations.conversation_id",
                    ondelete="CASCADE",
                ),
                nullable=False,
            ),
            sa.Column("sender", sa.String(length=32), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column(
                "guidance_level",
                sa.Integer(),
                nullable=False,
                server_default="1",
            ),
            sa.Column("metadata_json", sa.JSON(), nullable=False),
            sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
        )
        op.create_index(
            "ix_mentoring_msg_conversation_id",
            "mentoring_messages",
            ["conversation_id"],
        )
        op.create_index(
            "ix_mentoring_msg_created_at",
            "mentoring_messages",
            ["created_at"],
        )
        op.create_index(
            "ix_mentor_msg_conv_time",
            "mentoring_messages",
            ["conversation_id", "created_at"],
        )

    # 7. Create developer_reports table
    if "developer_reports" not in existing_tables:
        op.create_table(
            "developer_reports",
            sa.Column("report_id", sa.String(length=64), primary_key=True),
            sa.Column(
                "developer_id",
                sa.String(length=64),
                sa.ForeignKey("developers.developer_id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("period_type", sa.String(length=32), nullable=False),
            sa.Column("start_date", mysql.DATETIME(fsp=6), nullable=False),
            sa.Column("end_date", mysql.DATETIME(fsp=6), nullable=False),
            sa.Column("metrics_json", sa.JSON(), nullable=False),
            sa.Column("content_json", sa.JSON(), nullable=False),
            sa.Column("generated_at", mysql.DATETIME(fsp=6), nullable=False),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
        )
        op.create_index(
            "ix_developer_reports_developer_id",
            "developer_reports",
            ["developer_id"],
        )
        op.create_index(
            "ix_developer_reports_period_type",
            "developer_reports",
            ["period_type"],
        )
        op.create_index(
            "ix_dev_reports_dev_time",
            "developer_reports",
            ["developer_id", "generated_at"],
        )

    # 8. Create mcp_audit_logs table
    if "mcp_audit_logs" not in existing_tables:
        op.create_table(
            "mcp_audit_logs",
            sa.Column("log_id", sa.String(length=64), primary_key=True),
            sa.Column("tool_name", sa.String(length=128), nullable=False),
            sa.Column("caller_id", sa.String(length=64), nullable=True),
            sa.Column("input_summary", sa.String(length=1024), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("duration_ms", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("timestamp", mysql.DATETIME(fsp=6), nullable=False),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
        )
        op.create_index("ix_mcp_audit_logs_tool_name", "mcp_audit_logs", ["tool_name"])
        op.create_index("ix_mcp_audit_logs_caller_id", "mcp_audit_logs", ["caller_id"])
        op.create_index("ix_mcp_audit_logs_timestamp", "mcp_audit_logs", ["timestamp"])


def downgrade() -> None:
    op.drop_table("mcp_audit_logs")
    op.drop_table("developer_reports")
    op.drop_table("mentoring_messages")
    op.drop_table("mentoring_conversations")
    op.drop_table("task_evaluations")
    op.drop_table("task_submissions")

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "personalized_tasks" in existing_tables:
        for col_name in [
            "evaluation_criteria_json",
            "expected_deliverables_json",
            "hints_json",
            "test_cases_json",
            "requirements_json",
            "learning_objectives_json",
            "problem_statement",
        ]:
            op.drop_column("personalized_tasks", col_name)

    if "developers" in existing_tables:
        for col_name in ["is_active", "role", "password_hash"]:
            op.drop_column("developers", col_name)
