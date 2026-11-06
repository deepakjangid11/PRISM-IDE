import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, sessionmaker

from prism.intelligence.models.developer_intelligence_models import (
    DeveloperFeedback,
    DeveloperInsight,
    DeveloperPerformanceSnapshot,
    FeedbackCategory,
    InsightCategory,
    InsightSeverity,
    LearningAdaptation,
    LearningStrategyType,
    PersonalizedTask,
    TaskDifficulty,
    TaskOutcome,
    TaskPriority,
    TaskStatus,
)
from prism.mentoring.models import (
    MentoringSessionRecord,
    MentoringStrategy,
)
from prism.storage.database import session_scope
from prism.storage.models.intelligence_records import (
    DeveloperFeedbackRecord,
    DeveloperInsightRecord,
    DeveloperPerformanceSnapshotRecord,
    LearningAdaptationRecord,
    MentoringSessionRecordEntity,
    PersonalizedTaskRecord,
    TaskOutcomeRecord,
)
from prism.storage.repositories.mysql_developer_repo import (
    MySQLDeveloperRepository,
)


def _ensure_utc(dt: datetime | None) -> datetime:
    """Ensure datetime has UTC timezone."""
    if dt is None:
        return datetime.now(UTC)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _parse_json_list(val: Any) -> list[Any]:
    """Defensively parse JSON value as list."""
    if val is None:
        return []
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError, ValueError, TypeError:
            return []
    return list(val) if hasattr(val, "__iter__") else []


def _parse_json_dict(val: Any) -> dict[str, Any]:
    """Defensively parse JSON value as dict."""
    if val is None:
        return {}
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError, ValueError, TypeError:
            return {}
    return dict(val) if hasattr(val, "items") else {}


class MySQLIntelligenceRepository:
    """MySQL-backed repository for developer intelligence, tasks, feedback, and mentoring records."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        developer_repo: MySQLDeveloperRepository | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.developer_repo = developer_repo or MySQLDeveloperRepository(
            session_factory
        )

    # =========================================================================
    # DEVELOPER INSIGHTS
    # =========================================================================

    def save_insight(self, insight: DeveloperInsight) -> None:
        """Persist structured developer insight after ensuring developer existence."""
        self.developer_repo.ensure_developer(insight.developer_id)
        with session_scope(self.session_factory) as session:
            record = DeveloperInsightRecord(
                insight_id=insight.insight_id,
                developer_id=insight.developer_id,
                category=insight.category.value
                if hasattr(insight.category, "value")
                else str(insight.category),
                title=insight.title,
                description=insight.description,
                severity=insight.severity.value
                if hasattr(insight.severity, "value")
                else str(insight.severity),
                evidence_json=list(insight.evidence),
                supporting_skills_json=list(insight.supporting_skills),
                actionable_recommendation=insight.actionable_recommendation,
                created_at=insight.timestamp,
            )
            session.merge(record)

    def get_insights(
        self, developer_id: str, limit: int = 50, offset: int = 0
    ) -> list[DeveloperInsight]:
        """Fetch developer insights in reverse chronological order."""
        with session_scope(self.session_factory) as session:
            stmt = (
                select(DeveloperInsightRecord)
                .where(DeveloperInsightRecord.developer_id == developer_id.strip())
                .order_by(desc(DeveloperInsightRecord.created_at))
                .offset(offset)
                .limit(limit)
            )
            records = session.scalars(stmt).all()
            return [
                DeveloperInsight(
                    insight_id=r.insight_id,
                    developer_id=r.developer_id,
                    category=InsightCategory(r.category),
                    title=r.title,
                    description=r.description,
                    severity=InsightSeverity(r.severity),
                    evidence=_parse_json_list(r.evidence_json),
                    supporting_skills=_parse_json_list(r.supporting_skills_json),
                    actionable_recommendation=r.actionable_recommendation,
                    timestamp=_ensure_utc(r.created_at),
                )
                for r in records
            ]

    # =========================================================================
    # PERFORMANCE SNAPSHOTS
    # =========================================================================

    def save_snapshot(self, snapshot: DeveloperPerformanceSnapshot) -> None:
        """Persist performance checkpoint."""
        self.developer_repo.ensure_developer(snapshot.developer_id)
        with session_scope(self.session_factory) as session:
            record = DeveloperPerformanceSnapshotRecord(
                snapshot_id=snapshot.snapshot_id,
                developer_id=snapshot.developer_id,
                timestamp=snapshot.timestamp,
                total_activities=snapshot.total_activities,
                verified_skills_count=snapshot.verified_skills_count,
                average_proficiency_score=snapshot.average_proficiency_score,
                active_knowledge_gaps_count=snapshot.active_knowledge_gaps_count,
                tasks_completed_count=snapshot.tasks_completed_count,
                task_success_rate=snapshot.task_success_rate,
                learning_consistency_score=snapshot.learning_consistency_score,
                role_readiness_json=dict(snapshot.role_readiness_scores),
            )
            session.merge(record)

    def get_snapshots(
        self, developer_id: str, limit: int = 50, offset: int = 0
    ) -> list[DeveloperPerformanceSnapshot]:
        """Fetch performance snapshots in reverse chronological order."""
        with session_scope(self.session_factory) as session:
            stmt = (
                select(DeveloperPerformanceSnapshotRecord)
                .where(
                    DeveloperPerformanceSnapshotRecord.developer_id
                    == developer_id.strip()
                )
                .order_by(desc(DeveloperPerformanceSnapshotRecord.timestamp))
                .offset(offset)
                .limit(limit)
            )
            records = session.scalars(stmt).all()
            return [
                DeveloperPerformanceSnapshot(
                    snapshot_id=r.snapshot_id,
                    developer_id=r.developer_id,
                    timestamp=_ensure_utc(r.timestamp),
                    total_activities=r.total_activities,
                    verified_skills_count=r.verified_skills_count,
                    average_proficiency_score=r.average_proficiency_score,
                    active_knowledge_gaps_count=r.active_knowledge_gaps_count,
                    tasks_completed_count=r.tasks_completed_count,
                    task_success_rate=r.task_success_rate,
                    learning_consistency_score=r.learning_consistency_score,
                    role_readiness_scores=_parse_json_dict(r.role_readiness_json),
                )
                for r in records
            ]

    def get_latest_snapshot(
        self, developer_id: str
    ) -> DeveloperPerformanceSnapshot | None:
        """Fetch most recent performance snapshot."""
        snapshots = self.get_snapshots(developer_id, limit=1)
        return snapshots[0] if snapshots else None

    # =========================================================================
    # PERSONALIZED TASKS
    # =========================================================================

    def save_task(self, task: PersonalizedTask) -> None:
        """Persist personalized learning task."""
        self.developer_repo.ensure_developer(task.developer_id)
        with session_scope(self.session_factory) as session:
            record = PersonalizedTaskRecord(
                task_id=task.task_id,
                developer_id=task.developer_id,
                title=task.title,
                description=task.description,
                target_skill=task.target_skill,
                difficulty=task.difficulty.value
                if hasattr(task.difficulty, "value")
                else str(task.difficulty),
                priority=task.priority.value
                if hasattr(task.priority, "value")
                else str(task.priority),
                status=task.status.value
                if hasattr(task.status, "value")
                else str(task.status),
                estimated_minutes=task.estimated_minutes,
                target_role=task.target_role,
                prerequisite_skills_json=list(task.prerequisite_skills),
                reason=task.reason,
                acceptance_criteria_json=list(task.acceptance_criteria),
                created_at=task.created_at,
                updated_at=task.updated_at,
            )
            session.merge(record)

    def get_task(self, task_id: str) -> PersonalizedTask | None:
        """Fetch personalized task by ID."""
        with session_scope(self.session_factory) as session:
            record = session.get(PersonalizedTaskRecord, task_id.strip())
            if not record:
                return None
            return PersonalizedTask(
                task_id=record.task_id,
                developer_id=record.developer_id,
                title=record.title,
                description=record.description,
                target_skill=record.target_skill,
                difficulty=TaskDifficulty(record.difficulty),
                priority=TaskPriority(record.priority),
                status=TaskStatus(record.status),
                estimated_minutes=record.estimated_minutes,
                target_role=record.target_role,
                prerequisite_skills=_parse_json_list(record.prerequisite_skills_json),
                reason=record.reason,
                acceptance_criteria=_parse_json_list(record.acceptance_criteria_json),
                created_at=_ensure_utc(record.created_at),
                updated_at=_ensure_utc(record.updated_at),
            )

    def get_tasks_for_developer(
        self,
        developer_id: str,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PersonalizedTask]:
        """Fetch personalized tasks for developer, optionally filtered by status."""
        with session_scope(self.session_factory) as session:
            stmt = select(PersonalizedTaskRecord).where(
                PersonalizedTaskRecord.developer_id == developer_id.strip()
            )
            if status is not None:
                stmt = stmt.where(
                    PersonalizedTaskRecord.status == status.strip().lower()
                )
            stmt = (
                stmt.order_by(desc(PersonalizedTaskRecord.created_at))
                .offset(offset)
                .limit(limit)
            )

            records = session.scalars(stmt).all()
            return [
                PersonalizedTask(
                    task_id=r.task_id,
                    developer_id=r.developer_id,
                    title=r.title,
                    description=r.description,
                    target_skill=r.target_skill,
                    difficulty=TaskDifficulty(r.difficulty),
                    priority=TaskPriority(r.priority),
                    status=TaskStatus(r.status),
                    estimated_minutes=r.estimated_minutes,
                    target_role=r.target_role,
                    prerequisite_skills=_parse_json_list(r.prerequisite_skills_json),
                    reason=r.reason,
                    acceptance_criteria=_parse_json_list(r.acceptance_criteria_json),
                    created_at=_ensure_utc(r.created_at),
                    updated_at=_ensure_utc(r.updated_at),
                )
                for r in records
            ]

    def update_task_status(
        self, task_id: str, status: TaskStatus | str
    ) -> PersonalizedTask | None:
        """Update task status with timestamp refresh."""
        now = datetime.now(UTC)
        status_str = status.value if hasattr(status, "value") else str(status)

        with session_scope(self.session_factory) as session:
            record = session.get(PersonalizedTaskRecord, task_id.strip())
            if not record:
                return None
            record.status = status_str
            record.updated_at = now
            session.commit()
            return PersonalizedTask(
                task_id=record.task_id,
                developer_id=record.developer_id,
                title=record.title,
                description=record.description,
                target_skill=record.target_skill,
                difficulty=TaskDifficulty(record.difficulty),
                priority=TaskPriority(record.priority),
                status=TaskStatus(record.status),
                estimated_minutes=record.estimated_minutes,
                target_role=record.target_role,
                prerequisite_skills=_parse_json_list(record.prerequisite_skills_json),
                reason=record.reason,
                acceptance_criteria=_parse_json_list(record.acceptance_criteria_json),
                created_at=_ensure_utc(record.created_at),
                updated_at=_ensure_utc(record.updated_at),
            )

    # =========================================================================
    # TASK OUTCOMES
    # =========================================================================

    def save_task_outcome(self, outcome: TaskOutcome) -> None:
        """Record executed task outcome."""
        self.developer_repo.ensure_developer(outcome.developer_id)
        with session_scope(self.session_factory) as session:
            record = TaskOutcomeRecord(
                outcome_id=outcome.outcome_id,
                task_id=outcome.task_id,
                developer_id=outcome.developer_id,
                success=outcome.success,
                execution_notes=outcome.execution_notes,
                verified_artifacts_json=list(outcome.verified_artifacts),
                recorded_at=outcome.recorded_at,
            )
            session.merge(record)

    def get_task_outcomes(
        self, developer_id: str, task_id: str | None = None
    ) -> list[TaskOutcome]:
        """Fetch task outcomes."""
        with session_scope(self.session_factory) as session:
            stmt = select(TaskOutcomeRecord).where(
                TaskOutcomeRecord.developer_id == developer_id.strip()
            )
            if task_id is not None:
                stmt = stmt.where(TaskOutcomeRecord.task_id == task_id.strip())
            stmt = stmt.order_by(desc(TaskOutcomeRecord.recorded_at))
            records = session.scalars(stmt).all()
            return [
                TaskOutcome(
                    outcome_id=r.outcome_id,
                    task_id=r.task_id,
                    developer_id=r.developer_id,
                    success=r.success,
                    execution_notes=r.execution_notes,
                    verified_artifacts=_parse_json_list(r.verified_artifacts_json),
                    recorded_at=_ensure_utc(r.recorded_at),
                )
                for r in records
            ]

    # =========================================================================
    # DEVELOPER FEEDBACK
    # =========================================================================

    def save_feedback(self, feedback: DeveloperFeedback) -> None:
        """Persist developer feedback."""
        self.developer_repo.ensure_developer(feedback.developer_id)
        with session_scope(self.session_factory) as session:
            record = DeveloperFeedbackRecord(
                feedback_id=feedback.feedback_id,
                developer_id=feedback.developer_id,
                related_task_id=feedback.related_task_id,
                related_skill=feedback.related_skill,
                category=feedback.category.value
                if hasattr(feedback.category, "value")
                else str(feedback.category),
                message=feedback.message,
                supporting_evidence_json=list(feedback.supporting_evidence),
                recommended_next_action=feedback.recommended_next_action,
                confidence_level=feedback.confidence_level,
                timestamp=feedback.timestamp,
            )
            session.merge(record)

    def get_feedbacks(
        self, developer_id: str, limit: int = 50, offset: int = 0
    ) -> list[DeveloperFeedback]:
        """Fetch developer feedback records."""
        with session_scope(self.session_factory) as session:
            stmt = (
                select(DeveloperFeedbackRecord)
                .where(DeveloperFeedbackRecord.developer_id == developer_id.strip())
                .order_by(desc(DeveloperFeedbackRecord.timestamp))
                .offset(offset)
                .limit(limit)
            )
            records = session.scalars(stmt).all()
            return [
                DeveloperFeedback(
                    feedback_id=r.feedback_id,
                    developer_id=r.developer_id,
                    related_task_id=r.related_task_id,
                    related_skill=r.related_skill,
                    category=FeedbackCategory(r.category),
                    message=r.message,
                    supporting_evidence=_parse_json_list(r.supporting_evidence_json),
                    recommended_next_action=r.recommended_next_action,
                    confidence_level=r.confidence_level,
                    timestamp=_ensure_utc(r.timestamp),
                )
                for r in records
            ]

    # =========================================================================
    # MENTORING SESSIONS
    # =========================================================================

    def save_mentoring_session(self, session: MentoringSessionRecord) -> None:
        """Persist adaptive mentoring interaction record."""
        self.developer_repo.ensure_developer(session.developer_id)
        with session_scope(self.session_factory) as session_scope_ctx:
            record = MentoringSessionRecordEntity(
                session_id=session.session_id,
                developer_id=session.developer_id,
                strategy=session.strategy.value
                if hasattr(session.strategy, "value")
                else str(session.strategy),
                query=session.query,
                target_skill=session.target_skill,
                summary=session.summary,
                outcome_rating=session.outcome_rating,
                outcome_notes=session.outcome_notes,
                provider_used=session.provider_used,
                metadata_json=session.metadata_json or {},
                created_at=session.created_at,
            )
            session_scope_ctx.merge(record)

    def get_mentoring_sessions(
        self, developer_id: str, limit: int = 50, offset: int = 0
    ) -> list[MentoringSessionRecord]:
        """Fetch mentoring sessions for developer."""
        with session_scope(self.session_factory) as session:
            stmt = (
                select(MentoringSessionRecordEntity)
                .where(
                    MentoringSessionRecordEntity.developer_id == developer_id.strip()
                )
                .order_by(desc(MentoringSessionRecordEntity.created_at))
                .offset(offset)
                .limit(limit)
            )
            records = session.scalars(stmt).all()
            return [
                MentoringSessionRecord(
                    session_id=r.session_id,
                    developer_id=r.developer_id,
                    strategy=MentoringStrategy(r.strategy),
                    query=r.query,
                    target_skill=r.target_skill,
                    summary=r.summary,
                    outcome_rating=r.outcome_rating,
                    outcome_notes=r.outcome_notes,
                    provider_used=r.provider_used,
                    metadata_json=_parse_json_dict(r.metadata_json),
                    created_at=_ensure_utc(r.created_at),
                )
                for r in records
            ]

    # =========================================================================
    # LEARNING ADAPTATIONS
    # =========================================================================

    def save_adaptation(self, adaptation: LearningAdaptation) -> None:
        """Persist learning adaptation event."""
        self.developer_repo.ensure_developer(adaptation.developer_id)
        with session_scope(self.session_factory) as session:
            record = LearningAdaptationRecord(
                adaptation_id=adaptation.adaptation_id,
                developer_id=adaptation.developer_id,
                previous_strategy=adaptation.previous_strategy,
                new_strategy=adaptation.new_strategy.value
                if hasattr(adaptation.new_strategy, "value")
                else str(adaptation.new_strategy),
                adaptation_reason=adaptation.adaptation_reason,
                adjusted_difficulty=adaptation.adjusted_difficulty.value
                if hasattr(adaptation.adjusted_difficulty, "value")
                else str(adaptation.adjusted_difficulty),
                adjusted_priorities_json=dict(adaptation.adjusted_priorities),
                stalled_skills_json=list(adaptation.stalled_skills_detected),
                timestamp=adaptation.timestamp,
            )
            session.merge(record)

    def get_adaptations(
        self, developer_id: str, limit: int = 50, offset: int = 0
    ) -> list[LearningAdaptation]:
        """Fetch learning adaptations for developer."""
        with session_scope(self.session_factory) as session:
            stmt = (
                select(LearningAdaptationRecord)
                .where(LearningAdaptationRecord.developer_id == developer_id.strip())
                .order_by(desc(LearningAdaptationRecord.timestamp))
                .offset(offset)
                .limit(limit)
            )
            records = session.scalars(stmt).all()
            return [
                LearningAdaptation(
                    adaptation_id=r.adaptation_id,
                    developer_id=r.developer_id,
                    previous_strategy=r.previous_strategy,
                    new_strategy=LearningStrategyType(r.new_strategy),
                    adaptation_reason=r.adaptation_reason,
                    adjusted_difficulty=TaskDifficulty(r.adjusted_difficulty),
                    adjusted_priorities=_parse_json_dict(r.adjusted_priorities_json),
                    stalled_skills_detected=_parse_json_list(r.stalled_skills_json),
                    timestamp=_ensure_utc(r.timestamp),
                )
                for r in records
            ]

    def get_latest_adaptation(self, developer_id: str) -> LearningAdaptation | None:
        """Fetch most recent learning adaptation."""
        adaptations = self.get_adaptations(developer_id, limit=1)
        return adaptations[0] if adaptations else None
