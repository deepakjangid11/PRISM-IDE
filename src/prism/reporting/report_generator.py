import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from prism.intelligence.models.developer_intelligence_models import (
    TaskStatus,
)
from prism.intelligence.models.task_platform_models import (
    DeveloperReport,
)
from prism.intelligence.skill_tracker import SkillTracker
from prism.logging.logger import get_logger
from prism.storage.repositories.base import (
    ActivityRepository,
    DeveloperRepository,
    IntelligenceRepository,
    TaskPlatformRepository,
)

logger = get_logger(__name__)


class DeveloperReportGenerator:
    """Production reporting engine aggregating verifiable developer metrics, task completions,

    skill growth, and personalized learning milestones.
    """

    def __init__(
        self,
        task_platform_repo: TaskPlatformRepository,
        intelligence_repo: IntelligenceRepository,
        skill_tracker: SkillTracker,
        developer_repo: DeveloperRepository,
        activity_repo: ActivityRepository | None = None,
    ) -> None:
        self.task_platform_repo = task_platform_repo
        self.intelligence_repo = intelligence_repo
        self.skill_tracker = skill_tracker
        self.developer_repo = developer_repo
        self.activity_repo = activity_repo

    def generate_report(
        self,
        developer_id: str,
        period_type: str = "weekly",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> DeveloperReport:
        """Generate, compute, and persist a structured progress report for a developer."""
        cleaned_dev_id = developer_id.strip()
        dev_profile = self.developer_repo.get_developer(cleaned_dev_id)
        if not dev_profile:
            raise ValueError(f"Developer with ID '{cleaned_dev_id}' not found")

        now = datetime.now(UTC)
        p_type = period_type.strip().lower()

        # 1. Establish Reporting Boundaries
        if p_type == "daily":
            calc_end = end_date or now
            calc_start = start_date or (calc_end - timedelta(days=1))
        elif p_type == "monthly":
            calc_end = end_date or now
            calc_start = start_date or (calc_end - timedelta(days=30))
        elif p_type == "custom":
            calc_end = end_date or now
            calc_start = start_date or (calc_end - timedelta(days=7))
        else:  # default weekly
            p_type = "weekly"
            calc_end = end_date or now
            calc_start = start_date or (calc_end - timedelta(days=7))

        # 2. Gather Data from Repositories
        all_tasks = self.intelligence_repo.get_tasks_for_developer(
            cleaned_dev_id, limit=200
        )
        period_tasks = [
            t
            for t in all_tasks
            if calc_start <= t.created_at <= calc_end
            or calc_start <= t.updated_at <= calc_end
        ]

        all_evaluations = self.task_platform_repo.get_evaluations_for_developer(
            cleaned_dev_id, limit=200
        )
        period_evaluations = [
            e for e in all_evaluations if calc_start <= e.evaluated_at <= calc_end
        ]

        skill_profile = self.skill_tracker.get_profile(cleaned_dev_id)
        period_evidence = [
            ev
            for s in skill_profile.skills.values()
            for ev in s.evidence_list
            if calc_start <= ev.timestamp <= calc_end
        ]

        # 3. Compute Real Metrics
        assigned_count = len(period_tasks)
        completed_count = sum(
            1 for t in period_tasks if t.status == TaskStatus.COMPLETED
        )
        pending_count = sum(
            1
            for t in period_tasks
            if t.status
            in (
                TaskStatus.GENERATED,
                TaskStatus.ACCEPTED,
                TaskStatus.IN_PROGRESS,
                TaskStatus.SUBMITTED,
            )
        )

        passed_evals = [e for e in period_evaluations if e.passed]
        failed_evals = [e for e in period_evaluations if not e.passed]
        failed_attempts_count = len(failed_evals)

        avg_score = (
            round(
                sum(e.score for e in period_evaluations) / len(period_evaluations),
                1,
            )
            if period_evaluations
            else 0.0
        )

        completion_rate = (
            round((completed_count / assigned_count) * 100, 1)
            if assigned_count > 0
            else 0.0
        )

        # Skills improved
        improved_skills = list(dict.fromkeys(ev.skill_name for ev in period_evidence))

        # Skills needing attention
        attention_skills = list(
            dict.fromkeys(
                t.target_skill
                for t in period_tasks
                if t.status in (TaskStatus.FAILED, TaskStatus.IN_PROGRESS)
            )
        )

        # Consistency calculation: active days with task or activity events
        active_dates = {t.created_at.date() for t in period_tasks}
        active_dates.update(e.evaluated_at.date() for e in period_evaluations)
        days_in_period = max((calc_end.date() - calc_start.date()).days, 1)
        consistency_pct = round(min(len(active_dates) / days_in_period, 1.0) * 100, 1)

        # 4. Formulate Verifiable Achievements and Actionable Goals
        achievements: list[str] = []
        if completed_count > 0:
            achievements.append(
                f"Successfully completed {completed_count} hands-on development task(s) during this period."
            )
        if improved_skills:
            achievements.append(
                f"Demonstrated verified skill evidence in: {', '.join(improved_skills)}."
            )
        if avg_score >= 80.0 and period_evaluations:
            achievements.append(
                f"Achieved a high average evaluation score of {avg_score}/100 across submissions."
            )
        if not achievements:
            achievements.append(
                "Started active learning path onboarding and initial task exploration."
            )

        recommended_goals: list[str] = []
        if attention_skills:
            for s in attention_skills[:2]:
                recommended_goals.append(
                    f"Bridge identified comprehension blockers in '{s}' by completing remediation practice exercises."
                )
        if pending_count > 0:
            recommended_goals.append(
                f"Complete and submit the {pending_count} pending assigned task(s)."
            )
        if not recommended_goals:
            recommended_goals.append(
                "Advance to higher-difficulty integration challenges to broaden role readiness."
            )

        metrics_payload: dict[str, Any] = {
            "assigned_tasks": assigned_count,
            "completed_tasks": completed_count,
            "pending_tasks": pending_count,
            "passed_evaluations": len(passed_evals),
            "failed_attempts": failed_attempts_count,
            "average_evaluation_score": avg_score,
            "completion_rate_percentage": completion_rate,
            "learning_consistency_percentage": consistency_pct,
            "active_days_count": len(active_dates),
            "skills_improved_count": len(improved_skills),
        }

        content_payload: dict[str, Any] = {
            "developer": {
                "id": dev_profile["developer_id"],
                "name": dev_profile.get("name"),
                "email": dev_profile.get("email"),
            },
            "period": {
                "type": p_type,
                "start": calc_start.isoformat(),
                "end": calc_end.isoformat(),
            },
            "summary": {
                "headline": f"{p_type.capitalize()} Progress Summary for {dev_profile.get('name') or cleaned_dev_id}",
                "completed_tasks": completed_count,
                "assigned_tasks": assigned_count,
                "average_score": avg_score,
            },
            "skills_improved": improved_skills,
            "skills_requiring_attention": attention_skills,
            "key_achievements": achievements,
            "recommended_next_goals": recommended_goals,
            "recent_tasks_evaluated": [
                {
                    "evaluation_id": e.evaluation_id,
                    "task_id": e.task_id,
                    "score": e.score,
                    "passed": e.passed,
                    "status": e.completion_status.value
                    if hasattr(e.completion_status, "value")
                    else str(e.completion_status),
                }
                for e in period_evaluations[:5]
            ],
        }

        report = DeveloperReport(
            report_id=f"rep_{uuid.uuid4().hex[:12]}",
            developer_id=cleaned_dev_id,
            period_type=p_type,
            start_date=calc_start,
            end_date=calc_end,
            metrics=metrics_payload,
            content=content_payload,
            generated_at=now,
        )

        self.task_platform_repo.save_report(report)

        logger.info(
            "Progress report generated | rep=%s | dev=%s | period=%s | score=%.1f",
            report.report_id,
            cleaned_dev_id,
            p_type,
            avg_score,
        )
        return report

    def get_report(self, report_id: str) -> DeveloperReport | None:
        """Fetch report by ID."""
        return self.task_platform_repo.get_report(report_id)

    def list_reports(
        self, developer_id: str, limit: int = 50, offset: int = 0
    ) -> list[DeveloperReport]:
        """Fetch historical reports for developer."""
        return self.task_platform_repo.get_reports_for_developer(
            developer_id, limit=limit, offset=offset
        )
