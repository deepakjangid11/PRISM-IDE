from __future__ import annotations

from typing import TYPE_CHECKING, Any

from prism.intelligence.models.skill_models import DeveloperSkillProfile
from prism.learning.models import LearningPath, LearningProgress
from prism.logging.logger import get_logger

if TYPE_CHECKING:
    from prism.storage.repositories.base import LearningRepository

logger = get_logger(__name__)


class LearningProgressTracker:
    """Track and evaluate a developer's progress against a defined learning path."""

    def __init__(self, repository: LearningRepository | None = None) -> None:
        self._repository = repository

    def track_progress(
        self,
        developer_profile: DeveloperSkillProfile,
        learning_path: LearningPath,
    ) -> LearningProgress:
        """Evaluate completion status across each step of the learning path."""
        dev_id = developer_profile.developer_id
        target_goal = learning_path.target_goal

        completed_skills: list[str] = []
        in_progress_skills: list[str] = []
        remaining_skills: list[str] = []

        for step in learning_path.steps:
            dev_skill = developer_profile.get_skill(step)
            if dev_skill is None or dev_skill.evidence_count == 0:
                remaining_skills.append(step)
            elif dev_skill.has_sufficient_evidence:
                completed_skills.append(step)
            else:
                in_progress_skills.append(step)

        total_steps = len(learning_path.steps)
        completion_pct = (
            round((len(completed_skills) / total_steps) * 100, 1)
            if total_steps > 0
            else 100.0
        )

        progress = LearningProgress(
            developer_id=dev_id,
            target_goal=target_goal,
            completed_skills=completed_skills,
            in_progress_skills=in_progress_skills,
            remaining_skills=remaining_skills,
            completion_percentage=completion_pct,
        )

        if self._repository is not None:
            self._repository.save_progress(
                progress,
                path_steps=learning_path.steps,
                change_summary=f"Tracked progress towards {target_goal}",
            )

        logger.info(
            "Tracked learning progress | dev=%s | goal=%s | completed=%d/%d (%.1f%%)",
            dev_id,
            target_goal,
            len(completed_skills),
            total_steps,
            completion_pct,
        )

        return progress

    def get_progress(
        self, developer_id: str, target_goal: str
    ) -> LearningProgress | None:
        """Retrieve persisted learning progress if repository is attached."""
        if self._repository is not None:
            return self._repository.get_progress(developer_id, target_goal)
        return None

    def get_progress_history(
        self, developer_id: str, target_goal: str | None = None
    ) -> list[dict[str, Any]]:
        """Retrieve historical progress events if repository is attached."""
        if self._repository is not None:
            return self._repository.get_progress_history(developer_id, target_goal)
        return []
