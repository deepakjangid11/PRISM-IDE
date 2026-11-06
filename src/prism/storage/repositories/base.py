from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from datetime import datetime

    from prism.intelligence.models.developer_behavior_models import (
        DeveloperActivity,
    )
    from prism.intelligence.models.developer_identity_models import (
        DeveloperSession,
    )
    from prism.intelligence.models.developer_intelligence_models import (
        DeveloperFeedback,
        DeveloperInsight,
        DeveloperPerformanceSnapshot,
        LearningAdaptation,
        PersonalizedTask,
        TaskOutcome,
    )
    from prism.intelligence.models.skill_models import (
        DeveloperSkill,
        DeveloperSkillProfile,
        SkillEvidence,
        SkillRelationship,
    )
    from prism.intelligence.models.task_platform_models import (
        DetailedTaskEvaluation,
        DeveloperReport,
        MCPAuditLog,
        MentoringConversation,
        MentoringMessage,
        TaskSubmission,
    )
    from prism.learning.models import LearningProgress
    from prism.mentoring.models import MentoringSessionRecord


class DeveloperRepository(Protocol):
    """Protocol for developer master record operations."""

    def ensure_developer(
        self,
        developer_id: str,
        name: str | None = None,
        email: str | None = None,
    ) -> None:
        """Create developer if not existing or update timestamp."""
        ...

    def get_developer(self, developer_id: str) -> dict[str, Any] | None:
        """Fetch developer metadata by ID."""
        ...

    def get_by_email(self, email: str) -> dict[str, Any] | None:
        """Fetch developer metadata by email address."""
        ...

    def create_developer(
        self,
        developer_id: str,
        name: str | None = None,
        email: str | None = None,
    ) -> dict[str, Any]:
        """Create a new developer record, rejecting duplicates."""
        ...

    def create_user(
        self,
        developer_id: str,
        email: str,
        password_hash: str,
        name: str | None = None,
        role: str = "developer",
    ) -> dict[str, Any]:
        """Create a new authenticated user record."""
        ...

    def update_password(self, developer_id: str, password_hash: str) -> bool:
        """Update developer password hash."""
        ...

    def update_developer(
        self,
        developer_id: str,
        name: str | None = None,
        email: str | None = None,
    ) -> dict[str, Any] | None:
        """Update permitted developer profile fields."""
        ...

    def list_developers(self) -> list[str]:
        """Return list of all registered developer IDs."""
        ...


class ActivityRepository(Protocol):
    """Protocol for developer activity storage."""

    def save(self, activity: DeveloperActivity) -> None:
        """Persist a single developer activity event."""
        ...

    def save_many(self, activities: list[DeveloperActivity]) -> None:
        """Persist multiple developer activity events in a single batch."""
        ...

    def get_by_developer(
        self, developer_id: str, project_path: str | None = None
    ) -> list[DeveloperActivity]:
        """Fetch recorded activities for a developer, optionally filtered by project."""
        ...

    def get_by_session(self, session_id: str) -> list[DeveloperActivity]:
        """Fetch recorded activities associated with a specific working session."""
        ...

    def get_history(
        self,
        developer_id: str,
        project_path: str | None = None,
        session_id: str | None = None,
        language: str | None = None,
        category: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[DeveloperActivity], int]:
        """Fetch filtered and paginated activities with total count."""
        ...

    def clear(self, developer_id: str | None = None) -> None:
        """Remove recorded activities, optionally filtered by developer."""
        ...


class DeveloperSessionRepository(Protocol):
    """Protocol for persistent developer working sessions."""

    def create_session(self, session: DeveloperSession) -> None:
        """Persist a new developer session."""
        ...

    def get_session(self, session_id: str) -> DeveloperSession | None:
        """Retrieve a session by its unique session ID."""
        ...

    def get_active_session(self, developer_id: str) -> DeveloperSession | None:
        """Retrieve the currently active session for a developer."""
        ...

    def update_session(self, session: DeveloperSession) -> None:
        """Update an existing session state."""
        ...

    def touch_heartbeat(
        self,
        session_id: str,
        last_activity_at: datetime,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Update the last_activity_at timestamp and optionally metadata for an active session."""
        ...

    def list_sessions_for_developer(
        self, developer_id: str, limit: int = 50, offset: int = 0
    ) -> tuple[list[DeveloperSession], int]:
        """Retrieve paginated sessions for a developer and the total count."""
        ...

    def get_stale_sessions(self, cutoff_time: datetime) -> list[DeveloperSession]:
        """Retrieve active sessions whose last activity is before the cutoff time."""
        ...

    def terminate_session(
        self, session_id: str, status: str, ended_at: datetime
    ) -> bool:
        """Conclude an active session with the specified status and ended timestamp."""
        ...

    def clear(self, developer_id: str | None = None) -> None:
        """Remove sessions, optionally filtered by developer."""
        ...


class SkillRepository(Protocol):
    """Protocol for evidence and developer skill assessments."""

    def record_evidence(self, evidence: SkillEvidence) -> None:
        """Store verifiable concrete evidence for a skill."""
        ...

    def get_evidence(
        self, developer_id: str, skill_name: str | None = None
    ) -> list[SkillEvidence]:
        """Fetch recorded evidence for a developer, optionally filtered by skill."""
        ...

    def save_skill_assessment(self, skill: DeveloperSkill) -> None:
        """Save or update materialized skill assessment state."""
        ...

    def get_profile(self, developer_id: str) -> DeveloperSkillProfile:
        """Retrieve aggregated skill profile for a developer."""
        ...

    def list_developers(self) -> list[str]:
        """List all developers with recorded skill assessments."""
        ...


class SkillGraphRepository(Protocol):
    """Protocol for technical skill directory and graph topology."""

    def register_skill(
        self, skill_id: str, skill_name: str, category: str | None = None
    ) -> str:
        """Register a technical skill in the catalog, returning its stable skill_id."""
        ...

    def get_skill_id_by_name(self, skill_name: str) -> str | None:
        """Resolve a skill name to its stable surrogate skill_id."""
        ...

    def get_skill_name_by_id(self, skill_id: str) -> str | None:
        """Resolve a skill_id to its canonical skill name."""
        ...

    def add_relationship(self, relationship: SkillRelationship) -> None:
        """Add a directional relationship between skills."""
        ...

    def get_skills(self) -> list[str]:
        """Return all registered canonical skill names."""
        ...

    def get_relationships(self) -> list[SkillRelationship]:
        """Return all directed skill relationships."""
        ...


class LearningRepository(Protocol):
    """Protocol for learning roadmaps, normalized steps, and audit history."""

    def save_progress(
        self,
        progress: LearningProgress,
        path_steps: list[str] | None = None,
        change_summary: str | None = None,
    ) -> None:
        """Save normalized progress items and log an immutable history snapshot."""
        ...

    def get_progress(
        self, developer_id: str, target_goal: str
    ) -> LearningProgress | None:
        """Retrieve active learning progress by reconstructing normalized items."""
        ...

    def get_progress_history(
        self, developer_id: str, target_goal: str | None = None
    ) -> list[dict[str, Any]]:
        """Retrieve point-in-time progression checkpoints."""
        ...


class IntelligenceRepository(Protocol):
    """Protocol for developer intelligence, tasks, feedback, and mentoring records."""

    def save_insight(self, insight: DeveloperInsight) -> None:
        """Persist structured developer insight."""
        ...

    def get_insights(
        self, developer_id: str, limit: int = 50, offset: int = 0
    ) -> list[DeveloperInsight]:
        """Fetch developer insights in reverse chronological order."""
        ...

    def save_snapshot(self, snapshot: DeveloperPerformanceSnapshot) -> None:
        """Persist performance checkpoint."""
        ...

    def get_snapshots(
        self, developer_id: str, limit: int = 50, offset: int = 0
    ) -> list[DeveloperPerformanceSnapshot]:
        """Fetch performance snapshots in reverse chronological order."""
        ...

    def get_latest_snapshot(
        self, developer_id: str
    ) -> DeveloperPerformanceSnapshot | None:
        """Fetch most recent performance snapshot."""
        ...

    def save_task(self, task: PersonalizedTask) -> None:
        """Persist personalized learning task."""
        ...

    def get_task(self, task_id: str) -> PersonalizedTask | None:
        """Fetch personalized task by ID."""
        ...

    def get_tasks_for_developer(
        self,
        developer_id: str,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PersonalizedTask]:
        """Fetch personalized tasks for developer, optionally filtered by status."""
        ...

    def update_task_status(self, task_id: str, status: str) -> PersonalizedTask | None:
        """Update task lifecycle status."""
        ...

    def save_task_outcome(self, outcome: TaskOutcome) -> None:
        """Record executed task outcome."""
        ...

    def get_task_outcomes(
        self, developer_id: str, task_id: str | None = None
    ) -> list[TaskOutcome]:
        """Fetch task outcomes."""
        ...

    def save_feedback(self, feedback: DeveloperFeedback) -> None:
        """Persist developer feedback."""
        ...

    def get_feedbacks(
        self, developer_id: str, limit: int = 50, offset: int = 0
    ) -> list[DeveloperFeedback]:
        """Fetch developer feedback records."""
        ...

    def save_mentoring_session(self, session: MentoringSessionRecord) -> None:
        """Persist adaptive mentoring interaction record."""
        ...

    def get_mentoring_sessions(
        self, developer_id: str, limit: int = 50, offset: int = 0
    ) -> list[MentoringSessionRecord]:
        """Fetch mentoring sessions for developer."""
        ...

    def save_adaptation(self, adaptation: LearningAdaptation) -> None:
        """Persist learning adaptation event."""
        ...

    def get_adaptations(
        self, developer_id: str, limit: int = 50, offset: int = 0
    ) -> list[LearningAdaptation]:
        """Fetch learning adaptations for developer."""
        ...

    def get_latest_adaptation(self, developer_id: str) -> LearningAdaptation | None:
        """Fetch most recent learning adaptation."""
        ...


class TaskPlatformRepository(Protocol):
    """Protocol for task submissions, evaluations, mentoring conversations, reports, and MCP audits."""

    # Submissions
    def save_submission(self, submission: TaskSubmission) -> None:
        """Persist a developer's task submission."""
        ...

    def get_submission(self, submission_id: str) -> TaskSubmission | None:
        """Fetch a specific task submission by ID."""
        ...

    def get_submissions_for_task(self, task_id: str) -> list[TaskSubmission]:
        """Fetch all submissions for a given task."""
        ...

    def get_submissions_for_developer(
        self, developer_id: str, limit: int = 50, offset: int = 0
    ) -> list[TaskSubmission]:
        """Fetch submissions for a developer."""
        ...

    def update_submission_status(self, submission_id: str, status: str) -> None:
        """Update the processing status of a submission."""
        ...

    # Evaluations
    def save_evaluation(self, evaluation: DetailedTaskEvaluation) -> None:
        """Persist structured automated evaluation results."""
        ...

    def get_evaluation(self, evaluation_id: str) -> DetailedTaskEvaluation | None:
        """Fetch evaluation results by ID."""
        ...

    def get_evaluation_by_submission(
        self, submission_id: str
    ) -> DetailedTaskEvaluation | None:
        """Fetch evaluation result corresponding to a submission."""
        ...

    def get_evaluations_for_developer(
        self, developer_id: str, limit: int = 50, offset: int = 0
    ) -> list[DetailedTaskEvaluation]:
        """Fetch evaluation history for a developer."""
        ...

    # Mentoring Conversations & Messages
    def create_conversation(self, conversation: MentoringConversation) -> None:
        """Create or update a guided mentoring conversation."""
        ...

    def get_conversation(self, conversation_id: str) -> MentoringConversation | None:
        """Retrieve conversation metadata."""
        ...

    def get_conversations_for_developer(
        self, developer_id: str, task_id: str | None = None
    ) -> list[MentoringConversation]:
        """Retrieve developer conversations, optionally filtered by task."""
        ...

    def update_conversation_level(
        self, conversation_id: str, guidance_level: int
    ) -> None:
        """Update current progressive guidance level."""
        ...

    def save_message(self, message: MentoringMessage) -> None:
        """Save a message to conversation history."""
        ...

    def get_messages(
        self, conversation_id: str, limit: int = 100
    ) -> list[MentoringMessage]:
        """Retrieve messages in chronological order."""
        ...

    # Reports
    def save_report(self, report: DeveloperReport) -> None:
        """Persist a generated performance report."""
        ...

    def get_report(self, report_id: str) -> DeveloperReport | None:
        """Fetch a progress report by ID."""
        ...

    def get_reports_for_developer(
        self, developer_id: str, limit: int = 50, offset: int = 0
    ) -> list[DeveloperReport]:
        """Fetch reports for a developer."""
        ...

    # MCP Audit
    def save_mcp_audit(self, audit: MCPAuditLog) -> None:
        """Persist an MCP tool execution audit log entry."""
        ...

    def get_mcp_audits(
        self, caller_id: str | None = None, limit: int = 50
    ) -> list[MCPAuditLog]:
        """Fetch MCP audit logs."""
        ...
