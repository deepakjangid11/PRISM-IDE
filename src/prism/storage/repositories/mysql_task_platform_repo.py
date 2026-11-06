from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, sessionmaker

from prism.intelligence.models.task_platform_models import (
    DetailedTaskEvaluation,
    DeveloperReport,
    EvaluationCompletionStatus,
    MCPAuditLog,
    MentoringConversation,
    MentoringMessage,
    SubmissionStatus,
    SubmissionType,
    TaskSubmission,
    TestCaseResult,
)
from prism.storage.database import session_scope
from prism.storage.models.task_platform_records import (
    DeveloperReportRecord,
    MCPAuditLogRecord,
    MentoringConversationRecord,
    MentoringMessageRecord,
    TaskEvaluationRecord,
    TaskSubmissionRecord,
)
from prism.storage.repositories.base import DeveloperRepository


def _ensure_utc(dt: datetime) -> datetime:
    """Ensure datetime has UTC timezone."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _parse_json_list(val: Any) -> list[Any]:
    if isinstance(val, list):
        return val
    return []


def _parse_json_dict(val: Any) -> dict[str, Any]:
    if isinstance(val, dict):
        return val
    return {}


class MySQLTaskPlatformRepository:
    """MySQL-backed repository for submissions, evaluations, mentoring dialogues, reports, and MCP audits."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        developer_repo: DeveloperRepository | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.developer_repo = developer_repo

    # =========================================================================
    # SUBMISSIONS
    # =========================================================================

    def save_submission(self, submission: TaskSubmission) -> None:
        """Persist a developer task submission."""
        if self.developer_repo:
            self.developer_repo.ensure_developer(submission.developer_id)
        with session_scope(self.session_factory) as session:
            record = TaskSubmissionRecord(
                submission_id=submission.submission_id,
                task_id=submission.task_id,
                developer_id=submission.developer_id,
                submission_type=submission.submission_type.value
                if hasattr(submission.submission_type, "value")
                else str(submission.submission_type),
                source_code=submission.source_code,
                file_tree_json=dict(submission.file_tree),
                repo_url=submission.repo_url,
                explanation=submission.explanation,
                status=submission.status.value
                if hasattr(submission.status, "value")
                else str(submission.status),
                submitted_at=submission.submitted_at,
            )
            session.merge(record)

    def get_submission(self, submission_id: str) -> TaskSubmission | None:
        """Fetch a specific task submission by ID."""
        with session_scope(self.session_factory) as session:
            record = session.get(TaskSubmissionRecord, submission_id.strip())
            if not record:
                return None
            return TaskSubmission(
                submission_id=record.submission_id,
                task_id=record.task_id,
                developer_id=record.developer_id,
                submission_type=SubmissionType(record.submission_type),
                source_code=record.source_code,
                file_tree=_parse_json_dict(record.file_tree_json),
                repo_url=record.repo_url,
                explanation=record.explanation,
                status=SubmissionStatus(record.status),
                submitted_at=_ensure_utc(record.submitted_at),
            )

    def get_submissions_for_task(self, task_id: str) -> list[TaskSubmission]:
        """Fetch all submissions for a given task."""
        with session_scope(self.session_factory) as session:
            stmt = (
                select(TaskSubmissionRecord)
                .where(TaskSubmissionRecord.task_id == task_id.strip())
                .order_by(desc(TaskSubmissionRecord.submitted_at))
            )
            records = session.scalars(stmt).all()
            return [
                TaskSubmission(
                    submission_id=r.submission_id,
                    task_id=r.task_id,
                    developer_id=r.developer_id,
                    submission_type=SubmissionType(r.submission_type),
                    source_code=r.source_code,
                    file_tree=_parse_json_dict(r.file_tree_json),
                    repo_url=r.repo_url,
                    explanation=r.explanation,
                    status=SubmissionStatus(r.status),
                    submitted_at=_ensure_utc(r.submitted_at),
                )
                for r in records
            ]

    def get_submissions_for_developer(
        self, developer_id: str, limit: int = 50, offset: int = 0
    ) -> list[TaskSubmission]:
        """Fetch submissions for a developer."""
        with session_scope(self.session_factory) as session:
            stmt = (
                select(TaskSubmissionRecord)
                .where(TaskSubmissionRecord.developer_id == developer_id.strip())
                .order_by(desc(TaskSubmissionRecord.submitted_at))
                .offset(offset)
                .limit(limit)
            )
            records = session.scalars(stmt).all()
            return [
                TaskSubmission(
                    submission_id=r.submission_id,
                    task_id=r.task_id,
                    developer_id=r.developer_id,
                    submission_type=SubmissionType(r.submission_type),
                    source_code=r.source_code,
                    file_tree=_parse_json_dict(r.file_tree_json),
                    repo_url=r.repo_url,
                    explanation=r.explanation,
                    status=SubmissionStatus(r.status),
                    submitted_at=_ensure_utc(r.submitted_at),
                )
                for r in records
            ]

    def update_submission_status(self, submission_id: str, status: str) -> None:
        """Update the processing status of a submission."""
        with session_scope(self.session_factory) as session:
            record = session.get(TaskSubmissionRecord, submission_id.strip())
            if record:
                record.status = status.strip().lower()

    # =========================================================================
    # EVALUATIONS
    # =========================================================================

    def save_evaluation(self, evaluation: DetailedTaskEvaluation) -> None:
        """Persist structured automated evaluation results."""
        with session_scope(self.session_factory) as session:
            record = TaskEvaluationRecord(
                evaluation_id=evaluation.evaluation_id,
                submission_id=evaluation.submission_id,
                task_id=evaluation.task_id,
                developer_id=evaluation.developer_id,
                passed=evaluation.passed,
                score=evaluation.score,
                completion_status=evaluation.completion_status.value
                if hasattr(evaluation.completion_status, "value")
                else str(evaluation.completion_status),
                strengths_json=list(evaluation.strengths),
                mistakes_json=list(evaluation.mistakes),
                missing_requirements_json=list(evaluation.missing_requirements),
                improvement_suggestions_json=list(evaluation.improvement_suggestions),
                recommended_next_steps_json=list(evaluation.recommended_next_steps),
                test_results_json=[t.model_dump() for t in evaluation.test_results],
                feedback_message=evaluation.feedback_message,
                generated_evidence_id=evaluation.generated_evidence_id,
                evaluated_at=evaluation.evaluated_at,
            )
            session.merge(record)

    def get_evaluation(self, evaluation_id: str) -> DetailedTaskEvaluation | None:
        """Fetch evaluation results by ID."""
        with session_scope(self.session_factory) as session:
            record = session.get(TaskEvaluationRecord, evaluation_id.strip())
            if not record:
                return None
            return self._record_to_evaluation(record)

    def get_evaluation_by_submission(
        self, submission_id: str
    ) -> DetailedTaskEvaluation | None:
        """Fetch evaluation result corresponding to a submission."""
        with session_scope(self.session_factory) as session:
            stmt = select(TaskEvaluationRecord).where(
                TaskEvaluationRecord.submission_id == submission_id.strip()
            )
            record = session.scalar(stmt)
            if not record:
                return None
            return self._record_to_evaluation(record)

    def get_evaluations_for_developer(
        self, developer_id: str, limit: int = 50, offset: int = 0
    ) -> list[DetailedTaskEvaluation]:
        """Fetch evaluation history for a developer."""
        with session_scope(self.session_factory) as session:
            stmt = (
                select(TaskEvaluationRecord)
                .where(TaskEvaluationRecord.developer_id == developer_id.strip())
                .order_by(desc(TaskEvaluationRecord.evaluated_at))
                .offset(offset)
                .limit(limit)
            )
            records = session.scalars(stmt).all()
            return [self._record_to_evaluation(r) for r in records]

    def _record_to_evaluation(
        self, record: TaskEvaluationRecord
    ) -> DetailedTaskEvaluation:
        raw_tests = _parse_json_list(record.test_results_json)
        test_results = [
            TestCaseResult(
                name=t.get("name", "Test"),
                passed=bool(t.get("passed", False)),
                description=t.get("description", ""),
                error_message=t.get("error_message"),
                execution_time_ms=float(t.get("execution_time_ms", 0.0)),
            )
            if isinstance(t, dict)
            else TestCaseResult(name="Test", passed=True)
            for t in raw_tests
        ]
        return DetailedTaskEvaluation(
            evaluation_id=record.evaluation_id,
            submission_id=record.submission_id,
            task_id=record.task_id,
            developer_id=record.developer_id,
            passed=record.passed,
            score=record.score,
            completion_status=EvaluationCompletionStatus(record.completion_status),
            strengths=_parse_json_list(record.strengths_json),
            mistakes=_parse_json_list(record.mistakes_json),
            missing_requirements=_parse_json_list(record.missing_requirements_json),
            improvement_suggestions=_parse_json_list(
                record.improvement_suggestions_json
            ),
            recommended_next_steps=_parse_json_list(record.recommended_next_steps_json),
            test_results=test_results,
            feedback_message=record.feedback_message,
            generated_evidence_id=record.generated_evidence_id,
            evaluated_at=_ensure_utc(record.evaluated_at),
        )

    # =========================================================================
    # MENTORING CONVERSATIONS & MESSAGES
    # =========================================================================

    def create_conversation(self, conversation: MentoringConversation) -> None:
        """Create or update a guided mentoring conversation."""
        if self.developer_repo:
            self.developer_repo.ensure_developer(conversation.developer_id)
        with session_scope(self.session_factory) as session:
            record = MentoringConversationRecord(
                conversation_id=conversation.conversation_id,
                task_id=conversation.task_id,
                developer_id=conversation.developer_id,
                title=conversation.title,
                current_guidance_level=conversation.current_guidance_level,
                status=conversation.status,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
            )
            session.merge(record)

    def get_conversation(self, conversation_id: str) -> MentoringConversation | None:
        """Retrieve conversation metadata."""
        with session_scope(self.session_factory) as session:
            record = session.get(MentoringConversationRecord, conversation_id.strip())
            if not record:
                return None
            return MentoringConversation(
                conversation_id=record.conversation_id,
                task_id=record.task_id,
                developer_id=record.developer_id,
                title=record.title,
                current_guidance_level=record.current_guidance_level,
                status=record.status,
                created_at=_ensure_utc(record.created_at),
                updated_at=_ensure_utc(record.updated_at),
            )

    def get_conversations_for_developer(
        self, developer_id: str, task_id: str | None = None
    ) -> list[MentoringConversation]:
        """Retrieve developer conversations, optionally filtered by task."""
        with session_scope(self.session_factory) as session:
            stmt = select(MentoringConversationRecord).where(
                MentoringConversationRecord.developer_id == developer_id.strip()
            )
            if task_id:
                stmt = stmt.where(
                    MentoringConversationRecord.task_id == task_id.strip()
                )
            stmt = stmt.order_by(desc(MentoringConversationRecord.updated_at))
            records = session.scalars(stmt).all()
            return [
                MentoringConversation(
                    conversation_id=r.conversation_id,
                    task_id=r.task_id,
                    developer_id=r.developer_id,
                    title=r.title,
                    current_guidance_level=r.current_guidance_level,
                    status=r.status,
                    created_at=_ensure_utc(r.created_at),
                    updated_at=_ensure_utc(r.updated_at),
                )
                for r in records
            ]

    def update_conversation_level(
        self, conversation_id: str, guidance_level: int
    ) -> None:
        """Update current progressive guidance level."""
        with session_scope(self.session_factory) as session:
            record = session.get(MentoringConversationRecord, conversation_id.strip())
            if record:
                record.current_guidance_level = guidance_level
                record.updated_at = datetime.now(UTC)

    def save_message(self, message: MentoringMessage) -> None:
        """Save a message to conversation history."""
        with session_scope(self.session_factory) as session:
            record = MentoringMessageRecord(
                message_id=message.message_id,
                conversation_id=message.conversation_id,
                sender=message.sender,
                content=message.content,
                guidance_level=message.guidance_level,
                metadata_json=dict(message.metadata),
                created_at=message.created_at,
            )
            session.merge(record)

            conv = session.get(
                MentoringConversationRecord, message.conversation_id.strip()
            )
            if conv:
                conv.updated_at = message.created_at

    def get_messages(
        self, conversation_id: str, limit: int = 100
    ) -> list[MentoringMessage]:
        """Retrieve messages in chronological order."""
        with session_scope(self.session_factory) as session:
            stmt = (
                select(MentoringMessageRecord)
                .where(
                    MentoringMessageRecord.conversation_id == conversation_id.strip()
                )
                .order_by(MentoringMessageRecord.created_at)
                .limit(limit)
            )
            records = session.scalars(stmt).all()
            return [
                MentoringMessage(
                    message_id=r.message_id,
                    conversation_id=r.conversation_id,
                    sender=r.sender,
                    content=r.content,
                    guidance_level=r.guidance_level,
                    metadata=_parse_json_dict(r.metadata_json),
                    created_at=_ensure_utc(r.created_at),
                )
                for r in records
            ]

    # =========================================================================
    # REPORTS
    # =========================================================================

    def save_report(self, report: DeveloperReport) -> None:
        """Persist a generated performance report."""
        if self.developer_repo:
            self.developer_repo.ensure_developer(report.developer_id)
        with session_scope(self.session_factory) as session:
            record = DeveloperReportRecord(
                report_id=report.report_id,
                developer_id=report.developer_id,
                period_type=report.period_type,
                start_date=report.start_date,
                end_date=report.end_date,
                metrics_json=dict(report.metrics),
                content_json=dict(report.content),
                generated_at=report.generated_at,
            )
            session.merge(record)

    def get_report(self, report_id: str) -> DeveloperReport | None:
        """Fetch a progress report by ID."""
        with session_scope(self.session_factory) as session:
            record = session.get(DeveloperReportRecord, report_id.strip())
            if not record:
                return None
            return DeveloperReport(
                report_id=record.report_id,
                developer_id=record.developer_id,
                period_type=record.period_type,
                start_date=_ensure_utc(record.start_date),
                end_date=_ensure_utc(record.end_date),
                metrics=_parse_json_dict(record.metrics_json),
                content=_parse_json_dict(record.content_json),
                generated_at=_ensure_utc(record.generated_at),
            )

    def get_reports_for_developer(
        self, developer_id: str, limit: int = 50, offset: int = 0
    ) -> list[DeveloperReport]:
        """Fetch reports for a developer."""
        with session_scope(self.session_factory) as session:
            stmt = (
                select(DeveloperReportRecord)
                .where(DeveloperReportRecord.developer_id == developer_id.strip())
                .order_by(desc(DeveloperReportRecord.generated_at))
                .offset(offset)
                .limit(limit)
            )
            records = session.scalars(stmt).all()
            return [
                DeveloperReport(
                    report_id=r.report_id,
                    developer_id=r.developer_id,
                    period_type=r.period_type,
                    start_date=_ensure_utc(r.start_date),
                    end_date=_ensure_utc(r.end_date),
                    metrics=_parse_json_dict(r.metrics_json),
                    content=_parse_json_dict(r.content_json),
                    generated_at=_ensure_utc(r.generated_at),
                )
                for r in records
            ]

    # =========================================================================
    # MCP AUDIT
    # =========================================================================

    def save_mcp_audit(self, audit: MCPAuditLog) -> None:
        """Persist an MCP tool execution audit log entry."""
        with session_scope(self.session_factory) as session:
            record = MCPAuditLogRecord(
                log_id=audit.log_id,
                tool_name=audit.tool_name,
                caller_id=audit.caller_id,
                input_summary=audit.input_summary,
                status=audit.status,
                duration_ms=audit.duration_ms,
                timestamp=audit.timestamp,
            )
            session.add(record)

    def get_mcp_audits(
        self, caller_id: str | None = None, limit: int = 50
    ) -> list[MCPAuditLog]:
        """Fetch MCP audit logs."""
        with session_scope(self.session_factory) as session:
            stmt = select(MCPAuditLogRecord)
            if caller_id:
                stmt = stmt.where(MCPAuditLogRecord.caller_id == caller_id.strip())
            stmt = stmt.order_by(desc(MCPAuditLogRecord.timestamp)).limit(limit)
            records = session.scalars(stmt).all()
            return [
                MCPAuditLog(
                    log_id=r.log_id,
                    tool_name=r.tool_name,
                    caller_id=r.caller_id,
                    input_summary=r.input_summary,
                    status=r.status,
                    duration_ms=r.duration_ms,
                    timestamp=_ensure_utc(r.timestamp),
                )
                for r in records
            ]
