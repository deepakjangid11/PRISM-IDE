"""Intelligent Feedback Engine for PRISM IDE.

Generates actionable, evidence-grounded feedback based on developer
performance, skill progression, task evaluations, and knowledge gaps.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from prism.intelligence.models.developer_intelligence_models import (
    DeveloperFeedback,
    FeedbackCategory,
    PersonalizedTask,
    TaskEvaluation,
)
from prism.storage.repositories.base import IntelligenceRepository

logger = logging.getLogger(__name__)


class IntelligentFeedbackEngine:
    """Engine providing targeted feedback to developers across tasks and learning milestones."""

    def __init__(
        self,
        intelligence_repo: IntelligenceRepository,
        intelligence_engine: Any | None = None,
    ) -> None:
        self.intelligence_repo = intelligence_repo
        self.intelligence_engine = intelligence_engine

    def generate_feedback_for_task(
        self,
        evaluation: TaskEvaluation,
        task: PersonalizedTask | None = None,
    ) -> DeveloperFeedback:
        """Generate structured feedback following a task evaluation."""
        feedback_id = f"fb_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC)

        evidence: list[str] = []
        if evaluation.generated_evidence_id:
            evidence.append(f"Evidence ID: {evaluation.generated_evidence_id}")
        evidence.extend(evaluation.strengths_demonstrated)

        if evaluation.passed:
            if evaluation.score >= 0.85:
                category = FeedbackCategory.MILESTONE_ACHIEVED
                message = (
                    f"Outstanding execution on task {evaluation.task_id}! "
                    f"You achieved a score of {evaluation.score * 100:.1f}%. "
                    f"{evaluation.feedback_message}"
                )
                recommended_action = (
                    "Progress to an advanced challenge or solidify your knowledge by "
                    "reviewing related architectural patterns."
                )
            else:
                category = FeedbackCategory.POSITIVE
                message = (
                    f"Good work completing task {evaluation.task_id} with score {evaluation.score * 100:.1f}%. "
                    f"{evaluation.feedback_message}"
                )
                recommended_action = "Review recommended improvements to refine your implementation skills."
        else:
            category = FeedbackCategory.IMPROVEMENT_REQUIRED
            message = (
                f"Task {evaluation.task_id} did not pass verification (score {evaluation.score * 100:.1f}%). "
                f"{evaluation.feedback_message}"
            )
            evidence.extend(evaluation.improvement_areas)
            recommended_action = "Review prerequisite concepts and request targeted guided mentoring for this topic."

        feedback = DeveloperFeedback(
            feedback_id=feedback_id,
            developer_id=evaluation.developer_id,
            related_task_id=evaluation.task_id,
            related_skill=task.target_skill if task else None,
            category=category,
            message=message,
            supporting_evidence=evidence,
            recommended_next_action=recommended_action,
            confidence_level=0.95,
            timestamp=now,
        )

        try:
            self.intelligence_repo.save_feedback(feedback)
        except (KeyError, ValueError, AttributeError, RuntimeError, OSError) as e:
            logger.warning("Failed to persist task feedback %s: %s", feedback_id, e)

        return feedback

    def generate_proactive_feedback(self, developer_id: str) -> list[DeveloperFeedback]:
        """Generate proactive coaching feedback analyzing intelligence snapshots, gaps, and trends."""
        feedbacks: list[DeveloperFeedback] = []
        now = datetime.now(UTC)

        profile = None
        if self.intelligence_engine and hasattr(
            self.intelligence_engine, "get_profile"
        ):
            try:
                profile = self.intelligence_engine.get_profile(developer_id)
            except (KeyError, ValueError, AttributeError, RuntimeError, OSError) as e:
                logger.warning("Failed to fetch profile for proactive feedback: %s", e)

        if not profile or not profile.has_sufficient_data:
            fb = DeveloperFeedback(
                feedback_id=f"fb_{uuid.uuid4().hex[:12]}",
                developer_id=developer_id,
                category=FeedbackCategory.POSITIVE,
                message=(
                    "Welcome to PRISM! Start writing code and logging your development activities "
                    "to unlock deep intelligence and tailored learning recommendations."
                ),
                supporting_evidence=["Insufficient telemetry for full diagnostic."],
                recommended_next_action="Work on a project file or execute a recommended learning task.",
                confidence_level=0.8,
                timestamp=now,
            )
            feedbacks.append(fb)
            try:
                self.intelligence_repo.save_feedback(fb)
            except (KeyError, ValueError, AttributeError, RuntimeError, OSError) as e:
                logger.warning("Failed to save onboarding feedback: %s", e)
            return feedbacks

        # Active gaps feedback
        if profile.active_gaps:
            top_gap = profile.active_gaps[0]
            fb_gap = DeveloperFeedback(
                feedback_id=f"fb_{uuid.uuid4().hex[:12]}",
                developer_id=developer_id,
                related_skill=top_gap,
                category=FeedbackCategory.KNOWLEDGE_GAP,
                message=(
                    f"A knowledge gap in '{top_gap}' was identified. Closing this gap will "
                    f"significantly improve your role readiness."
                ),
                supporting_evidence=[f"Identified gap in {top_gap}"],
                recommended_next_action=f"Generate and complete a personalized task for {top_gap}.",
                confidence_level=0.9,
                timestamp=now,
            )
            feedbacks.append(fb_gap)
            try:
                self.intelligence_repo.save_feedback(fb_gap)
            except (KeyError, ValueError, AttributeError, RuntimeError, OSError) as e:
                logger.warning("Failed to save gap feedback: %s", e)

        # Critical weaknesses warning
        if profile.critical_weaknesses:
            weakness = profile.critical_weaknesses[0]
            fb_warn = DeveloperFeedback(
                feedback_id=f"fb_{uuid.uuid4().hex[:12]}",
                developer_id=developer_id,
                related_skill=weakness,
                category=FeedbackCategory.PERFORMANCE_WARNING,
                message=(
                    f"Skill activity in '{weakness}' indicates stagnation or low proficiency. "
                    "Focused deliberate practice is recommended."
                ),
                supporting_evidence=[f"Weakness detected in {weakness}"],
                recommended_next_action=f"Schedule guided adaptive mentoring on {weakness}.",
                confidence_level=0.85,
                timestamp=now,
            )
            feedbacks.append(fb_warn)
            try:
                self.intelligence_repo.save_feedback(fb_warn)
            except (KeyError, ValueError, AttributeError, RuntimeError, OSError) as e:
                logger.warning("Failed to save weakness feedback: %s", e)

        # Top strengths affirmation
        if profile.top_strengths:
            strength = profile.top_strengths[0]
            fb_pos = DeveloperFeedback(
                feedback_id=f"fb_{uuid.uuid4().hex[:12]}",
                developer_id=developer_id,
                related_skill=strength,
                category=FeedbackCategory.POSITIVE,
                message=(
                    f"Excellent proficiency demonstrated in '{strength}'. You have consistent "
                    "evidence confirming strong mastery in this domain."
                ),
                supporting_evidence=[f"High proficiency recorded for {strength}"],
                recommended_next_action="Leverage this skill to tackle advanced architectural challenges.",
                confidence_level=0.95,
                timestamp=now,
            )
            feedbacks.append(fb_pos)
            try:
                self.intelligence_repo.save_feedback(fb_pos)
            except (KeyError, ValueError, AttributeError, RuntimeError, OSError) as e:
                logger.warning("Failed to save strength feedback: %s", e)

        return feedbacks

    def get_feedback_history(
        self, developer_id: str, limit: int = 50
    ) -> list[DeveloperFeedback]:
        """Retrieve stored feedback entries for a developer."""
        return self.intelligence_repo.get_feedbacks(developer_id, limit=limit)
