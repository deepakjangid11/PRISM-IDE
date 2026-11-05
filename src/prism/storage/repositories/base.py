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
    from prism.intelligence.models.skill_models import (
        DeveloperSkill,
        DeveloperSkillProfile,
        SkillEvidence,
        SkillRelationship,
    )
    from prism.learning.models import LearningProgress


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
