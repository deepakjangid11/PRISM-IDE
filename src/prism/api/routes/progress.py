from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from prism.api.dependencies import (
    intelligence_engine,
    intelligence_repo,
    learning_repo,
    skill_tracker,
    task_platform_repo,
)
from prism.intelligence.models.developer_intelligence_models import (
    DeveloperPerformanceSnapshot,
    TaskStatus,
)
from prism.security import get_optional_current_user, verify_developer_ownership

router = APIRouter(prefix="/progress", tags=["Developer Progress"])


class DashboardMetricsResponse(BaseModel):
    developer_id: str
    total_assigned_tasks: int
    completed_tasks: int
    pending_tasks: int
    failed_attempts: int
    average_evaluation_score: float
    task_success_rate: float
    learning_consistency_score: float
    verified_skills_count: int
    active_knowledge_gaps_count: int
    top_strengths: list[str]
    critical_weaknesses: list[str]


@router.get("/{developer_id}/dashboard", response_model=DashboardMetricsResponse)
async def get_dashboard_metrics(
    developer_id: str,
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> DashboardMetricsResponse:
    """Retrieve high-level real-time dashboard progress metrics for a developer."""
    cleaned_id = developer_id.strip()
    verify_developer_ownership(cleaned_id, current_user)

    tasks = []
    if intelligence_repo:
        tasks = intelligence_repo.get_tasks_for_developer(cleaned_id, limit=200)

    assigned_count = len(tasks)
    completed_count = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
    pending_count = sum(
        1
        for t in tasks
        if t.status
        in (
            TaskStatus.GENERATED,
            TaskStatus.ACCEPTED,
            TaskStatus.IN_PROGRESS,
            TaskStatus.SUBMITTED,
        )
    )

    evaluations = task_platform_repo.get_evaluations_for_developer(
        cleaned_id, limit=200
    )
    failed_count = sum(1 for e in evaluations if not e.passed)
    avg_score = (
        round(sum(e.score for e in evaluations) / len(evaluations), 1)
        if evaluations
        else 0.0
    )
    success_rate = (
        round(
            (sum(1 for e in evaluations if e.passed) / len(evaluations)) * 100,
            1,
        )
        if evaluations
        else 0.0
    )

    profile = skill_tracker.get_profile(cleaned_id)
    verified_skills = sum(
        1 for s in profile.skills.values() if s.has_sufficient_evidence
    )

    intel_profile = intelligence_engine.get_profile(cleaned_id)

    # Consistency score from performance analytics snapshot or activity
    latest_snapshot = None
    if intelligence_repo:
        latest_snapshot = intelligence_repo.get_latest_snapshot(cleaned_id)

    consistency = (
        latest_snapshot.learning_consistency_score
        if latest_snapshot
        else (75.0 if completed_count > 0 else 0.0)
    )

    return DashboardMetricsResponse(
        developer_id=cleaned_id,
        total_assigned_tasks=assigned_count,
        completed_tasks=completed_count,
        pending_tasks=pending_count,
        failed_attempts=failed_count,
        average_evaluation_score=avg_score,
        task_success_rate=success_rate,
        learning_consistency_score=consistency,
        verified_skills_count=verified_skills,
        active_knowledge_gaps_count=len(intel_profile.active_gaps),
        top_strengths=intel_profile.top_strengths,
        critical_weaknesses=intel_profile.critical_weaknesses,
    )


@router.get("/{developer_id}/skills")
async def get_skills_progress(
    developer_id: str,
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> dict[str, Any]:
    """Retrieve detailed skill proficiency breakdown and evidence counts."""
    cleaned_id = developer_id.strip()
    verify_developer_ownership(cleaned_id, current_user)
    profile = skill_tracker.get_profile(cleaned_id)
    return {
        "developer_id": cleaned_id,
        "skills_count": len(profile.skills),
        "skills": {
            k: {
                "skill_name": v.skill_name,
                "proficiency_level": v.proficiency_level.value
                if hasattr(v.proficiency_level, "value")
                else str(v.proficiency_level),
                "evidence_count": v.evidence_count,
                "has_sufficient_evidence": v.has_sufficient_evidence,
                "last_assessed": v.last_assessed.isoformat()
                if v.last_assessed
                else None,
            }
            for k, v in profile.skills.items()
        },
    }


@router.get(
    "/{developer_id}/history",
    response_model=list[DeveloperPerformanceSnapshot],
)
async def get_performance_history(
    developer_id: str,
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> list[DeveloperPerformanceSnapshot]:
    """Retrieve historical performance snapshots for progress trend comparison."""
    cleaned_id = developer_id.strip()
    verify_developer_ownership(cleaned_id, current_user)
    if not intelligence_repo:
        return []
    return intelligence_repo.get_snapshots(
        developer_id=cleaned_id, limit=limit, offset=offset
    )


@router.get("/{developer_id}/learning-paths")
async def get_learning_path_progress(
    developer_id: str,
    target_goal: str | None = None,
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> list[dict[str, Any]]:
    """Retrieve learning progress history and target roadmap milestones."""
    cleaned_id = developer_id.strip()
    verify_developer_ownership(cleaned_id, current_user)
    if not learning_repo:
        return []
    return learning_repo.get_progress_history(
        developer_id=cleaned_id, target_goal=target_goal
    )
