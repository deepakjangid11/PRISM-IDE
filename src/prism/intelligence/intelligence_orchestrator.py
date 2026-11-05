"""Cross-Module Intelligence Orchestrator for PRISM IDE.

Coordinates the end-to-end intelligence feedback loop across Developer Activities,
Skill Evidence, Proficiency Tracking, Knowledge Gaps, Adaptive Mentoring,
Personalized Task Generation, and Learning Adaptation.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from prism.intelligence.developer_intelligence_engine import DeveloperIntelligenceEngine
from prism.intelligence.intelligent_feedback_engine import IntelligentFeedbackEngine
from prism.intelligence.models.developer_behavior_models import DeveloperActivity
from prism.intelligence.performance_analytics import DeveloperPerformanceAnalytics
from prism.intelligence.task_recommendation_engine import TaskRecommendationEngine
from prism.learning.learning_adaptation_engine import LearningAdaptationEngine
from prism.mentoring.adaptive_engine import AdaptiveMentoringEngine
from prism.storage.repositories.base import IntelligenceRepository

logger = logging.getLogger(__name__)


class CrossModuleIntelligenceOrchestrator:
    """Master orchestrator connecting all PRISM intelligence, learning, and mentoring subsystems."""

    def __init__(
        self,
        intelligence_repo: IntelligenceRepository,
        intelligence_engine: DeveloperIntelligenceEngine,
        performance_analytics: DeveloperPerformanceAnalytics,
        task_engine: TaskRecommendationEngine,
        feedback_engine: IntelligentFeedbackEngine,
        adaptation_engine: LearningAdaptationEngine,
        adaptive_mentor: AdaptiveMentoringEngine,
        skill_evidence_engine: Any | None = None,
        skill_tracker: Any | None = None,
        gap_analyzer: Any | None = None,
        session_service: Any | None = None,
    ) -> None:
        self.intelligence_repo = intelligence_repo
        self.intelligence_engine = intelligence_engine
        self.performance_analytics = performance_analytics
        self.task_engine = task_engine
        self.feedback_engine = feedback_engine
        self.adaptation_engine = adaptation_engine
        self.adaptive_mentor = adaptive_mentor
        self.skill_evidence_engine = skill_evidence_engine
        self.skill_tracker = skill_tracker
        self.gap_analyzer = gap_analyzer
        self.session_service = session_service

    def process_activity_and_recalibrate(
        self,
        activity: DeveloperActivity,
        auto_generate_tasks: bool = False,
    ) -> dict[str, Any]:
        """Ingest activity, extract evidence, update proficiency, recalibrate intelligence and feedback."""
        developer_id = activity.developer_id
        now = datetime.now(UTC)
        logger.info(
            "Orchestrating activity recalibration for dev=%s | activity=%s",
            developer_id,
            activity.event_id,
        )

        extracted_evidence_count = 0
        updated_skills: list[str] = []

        # 1. Extract and record skill evidence
        if self.skill_evidence_engine and hasattr(
            self.skill_evidence_engine, "extract_evidence_from_activity"
        ):
            try:
                evidences = self.skill_evidence_engine.extract_evidence_from_activity(
                    activity
                )
                extracted_evidence_count = len(evidences)
                if self.skill_tracker and hasattr(
                    self.skill_tracker, "record_evidence"
                ):
                    for ev in evidences:
                        self.skill_tracker.record_evidence(ev)
                        if ev.skill_name not in updated_skills:
                            updated_skills.append(ev.skill_name)
            except (KeyError, ValueError, AttributeError, RuntimeError, OSError) as e:
                logger.warning("Evidence extraction failed during orchestration: %s", e)

        # 2. Recalibrate Developer Intelligence Profile
        analysis_result = self.intelligence_engine.analyze_developer(developer_id)
        profile = analysis_result.profile

        # 3. Adapt learning strategy based on fresh intelligence
        adaptation = self.adaptation_engine.adapt_strategy(developer_id)

        # 4. Generate proactive coaching feedback
        feedbacks = self.feedback_engine.generate_proactive_feedback(developer_id)

        # 5. Optionally generate tasks
        tasks_count = 0
        if auto_generate_tasks:
            try:
                tasks = self.task_engine.generate_tasks(
                    developer_id=developer_id, limit=3
                )
                tasks_count = len(tasks)
            except (KeyError, ValueError, AttributeError, RuntimeError, OSError) as e:
                logger.warning(
                    "Task auto-generation failed during orchestration: %s", e
                )

        return {
            "status": "success",
            "developer_id": developer_id,
            "activity_id": activity.event_id,
            "evidence_extracted_count": extracted_evidence_count,
            "skills_updated": updated_skills,
            "profile_status": profile.overall_status,
            "has_sufficient_data": profile.has_sufficient_data,
            "active_gaps_count": len(profile.active_gaps),
            "current_learning_strategy": adaptation.new_strategy.value,
            "adjusted_difficulty": adaptation.adjusted_difficulty.value,
            "proactive_feedbacks_count": len(feedbacks),
            "tasks_recommended_count": tasks_count,
            "recalibrated_at": now.isoformat(),
        }

    def run_full_developer_sync(
        self,
        developer_id: str,
        target_role: str | None = None,
    ) -> dict[str, Any]:
        """Perform a complete synchronous recalculation and alignment across all subsystems."""
        now = datetime.now(UTC)
        logger.info("Running full developer intelligence sync for dev=%s", developer_id)

        # 1. Full skill recalculation
        if self.skill_tracker and hasattr(self.skill_tracker, "evaluate_all_skills"):
            try:
                self.skill_tracker.evaluate_all_skills(developer_id)
            except (KeyError, ValueError, AttributeError, RuntimeError, OSError) as e:
                logger.warning("Skill tracker recalculation failed: %s", e)

        # 2. Intelligence Profile Analysis
        analysis_result = self.intelligence_engine.analyze_developer(developer_id)
        profile = analysis_result.profile

        # 3. Performance Snapshot
        snapshot = self.performance_analytics.get_overview(developer_id)

        # 4. Strategy Adaptation
        adaptation = self.adaptation_engine.adapt_strategy(developer_id)

        # 5. Task Generation
        tasks = self.task_engine.generate_tasks(
            developer_id=developer_id,
            target_role=target_role,
            limit=5,
        )

        # 6. Proactive Feedback
        feedbacks = self.feedback_engine.generate_proactive_feedback(developer_id)

        return {
            "status": "synced",
            "developer_id": developer_id,
            "overall_status": profile.overall_status,
            "verified_skills_count": snapshot.verified_skills_count,
            "average_proficiency_score": snapshot.average_proficiency_score,
            "active_gaps_count": len(profile.active_gaps),
            "current_learning_strategy": adaptation.new_strategy.value,
            "recommended_tasks_count": len(tasks),
            "generated_feedback_count": len(feedbacks),
            "synced_at": now.isoformat(),
        }
