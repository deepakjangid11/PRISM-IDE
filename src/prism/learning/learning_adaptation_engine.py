"""Learning Adaptation Engine for PRISM IDE.

Dynamically adapts learning strategies, task difficulties, and pedagogical
priorities based on developer progression velocity, stalled skills, and task outcomes.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from prism.intelligence.models.developer_intelligence_models import (
    LearningAdaptation,
    LearningStrategyType,
    TaskDifficulty,
    TrendDirection,
)
from prism.storage.repositories.base import IntelligenceRepository

logger = logging.getLogger(__name__)


class LearningAdaptationEngine:
    """Dynamically calibrates developer learning strategies and difficulty levels."""

    def __init__(
        self,
        intelligence_repo: IntelligenceRepository,
        intelligence_engine: Any | None = None,
        gap_analyzer: Any | None = None,
    ) -> None:
        self.intelligence_repo = intelligence_repo
        self.intelligence_engine = intelligence_engine
        self.gap_analyzer = gap_analyzer

    def adapt_strategy(self, developer_id: str) -> LearningAdaptation:
        """Evaluate developer performance and determine the optimal adaptive strategy."""
        now = datetime.now(UTC)
        prev = self.intelligence_repo.get_latest_adaptation(developer_id)
        previous_strategy = prev.new_strategy.value if prev else "standard"

        # Check recent task outcomes
        outcomes = self.intelligence_repo.get_task_outcomes(developer_id)
        failure_rate = 0.0
        if outcomes:
            failures = sum(1 for o in outcomes if not o.success)
            failure_rate = failures / len(outcomes)

        # Check profile and trends
        profile = None
        stalled_skills: list[str] = []
        if self.intelligence_engine and hasattr(
            self.intelligence_engine, "get_profile"
        ):
            try:
                profile = self.intelligence_engine.get_profile(developer_id)
                for skill_name, trend in profile.trends.items():
                    if trend.direction in (
                        TrendDirection.REGRESSING,
                        TrendDirection.STABLE,
                    ):
                        stalled_skills.append(skill_name)
            except (KeyError, ValueError, AttributeError, RuntimeError, OSError) as e:
                logger.warning("Could not retrieve profile trends: %s", e)

        # Strategy selection logic
        adjusted_priorities: dict[str, str] = {}
        if outcomes and len(outcomes) >= 2 and failure_rate >= 0.5:
            new_strategy = LearningStrategyType.REMEDIATION
            adjusted_difficulty = TaskDifficulty.BEGINNER
            reason = (
                f"Elevated failure rate ({failure_rate * 100:.0f}%) across recent {len(outcomes)} "
                "tasks. Shifting to foundational remediation."
            )
        elif stalled_skills:
            new_strategy = LearningStrategyType.PRACTICE_INTENSIVE
            adjusted_difficulty = (
                prev.adjusted_difficulty if prev else TaskDifficulty.INTERMEDIATE
            )
            reason = (
                f"Stalled proficiency detected in: {', '.join(stalled_skills[:3])}. "
                "Prioritizing intensive hands-on practice."
            )
            for skill in stalled_skills:
                adjusted_priorities[skill] = "High - Stalled progression remediation"
        elif (
            outcomes
            and len(outcomes) >= 3
            and failure_rate == 0.0
            and profile
            and profile.has_sufficient_data
        ):
            new_strategy = LearningStrategyType.ACCELERATED
            adjusted_difficulty = TaskDifficulty.ADVANCED
            reason = (
                "Flawless task execution and rapid mastery progression detected. "
                "Accelerating curriculum with advanced challenges."
            )
        elif profile and profile.active_gaps and len(profile.active_gaps) >= 3:
            new_strategy = LearningStrategyType.PREREQUISITE_FIRST
            adjusted_difficulty = (
                prev.adjusted_difficulty if prev else TaskDifficulty.INTERMEDIATE
            )
            reason = (
                f"Identified {len(profile.active_gaps)} active knowledge gaps. "
                "Focusing on foundational prerequisite acquisition."
            )
            for gap in profile.active_gaps:
                adjusted_priorities[gap] = "High - Essential prerequisite gap"
        else:
            new_strategy = LearningStrategyType.STANDARD
            adjusted_difficulty = (
                prev.adjusted_difficulty if prev else TaskDifficulty.INTERMEDIATE
            )
            reason = "Consistent development velocity within expected tolerances."

        # Add profile gaps to priorities if not already populated
        if profile and profile.active_gaps:
            for gap in profile.active_gaps:
                if gap not in adjusted_priorities:
                    adjusted_priorities[gap] = "Medium - Active knowledge gap"

        adaptation = LearningAdaptation(
            adaptation_id=f"adapt_{uuid.uuid4().hex[:12]}",
            developer_id=developer_id,
            previous_strategy=previous_strategy,
            new_strategy=new_strategy,
            adaptation_reason=reason,
            adjusted_difficulty=adjusted_difficulty,
            adjusted_priorities=adjusted_priorities,
            stalled_skills_detected=stalled_skills,
            timestamp=now,
        )

        try:
            self.intelligence_repo.save_adaptation(adaptation)
        except (KeyError, ValueError, AttributeError, RuntimeError, OSError) as e:
            logger.warning("Failed to persist learning adaptation: %s", e)

        return adaptation

    def get_current_strategy(self, developer_id: str) -> LearningAdaptation | None:
        """Fetch the latest active adaptation for a developer."""
        return self.intelligence_repo.get_latest_adaptation(developer_id)

    def get_adaptation_history(
        self,
        developer_id: str,
        limit: int = 20,
    ) -> list[LearningAdaptation]:
        """Fetch historical adaptations for a developer."""
        return self.intelligence_repo.get_adaptations(developer_id, limit=limit)
