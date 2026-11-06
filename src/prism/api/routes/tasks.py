"""FastAPI routes for Personalized Task Recommendations."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from prism.api.dependencies import (
    evaluation_engine,
    task_engine,
    task_platform_repo,
)
from prism.intelligence.models.developer_intelligence_models import (
    PersonalizedTask,
    TaskEvaluation,
    TaskRecommendation,
    TaskStatus,
)
from prism.intelligence.models.task_platform_models import TaskSubmission
from prism.security import get_optional_current_user, verify_developer_ownership

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["Personalized Tasks"])


class GenerateTasksRequest(BaseModel):
    developer_id: str = Field(..., min_length=1)
    target_role: str | None = None
    target_goal: str | None = None
    difficulty_preference: str | None = None
    limit: int = Field(default=5, ge=1, le=20)


class UpdateTaskStatusRequest(BaseModel):
    status: TaskStatus
    notes: str | None = None


class AssignTaskRequest(BaseModel):
    developer_id: str = Field(..., min_length=1)


class SubmitTaskRequest(BaseModel):
    developer_id: str = Field(..., min_length=1)
    submission_type: str = Field(default="code")
    source_code: str | None = None
    file_tree: dict[str, str] = Field(default_factory=dict)
    repo_url: str | None = None
    explanation: str | None = None


class EvaluateTaskRequest(BaseModel):
    developer_id: str = Field(..., min_length=1)
    passed: bool
    score: float = Field(..., ge=0.0, le=1.0)
    execution_notes: str = ""
    verified_artifacts: list[str] = Field(default_factory=list)


@router.post("/generate", response_model=list[PersonalizedTask])
async def generate_tasks(
    request: GenerateTasksRequest,
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> list[PersonalizedTask]:
    """Generate targeted, gap-closing personalized tasks for a developer."""
    verify_developer_ownership(request.developer_id, current_user)
    try:
        recommendations = task_engine.generate_tasks(
            developer_id=request.developer_id,
            target_role=request.target_role,
            target_goal=request.target_goal,
            difficulty_preference=request.difficulty_preference,
            limit=request.limit,
        )
        return [rec.task for rec in recommendations]
    except Exception as err:
        logger.exception("Failed to generate tasks for %s", request.developer_id)
        raise HTTPException(
            status_code=500,
            detail="Internal server error generating personalized tasks",
        ) from err


@router.get("/recommendations/{developer_id}", response_model=list[TaskRecommendation])
async def get_task_recommendations(
    developer_id: str,
    target_role: str | None = None,
    limit: int = Query(default=5, ge=1, le=20),
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> list[TaskRecommendation]:
    """Retrieve prioritized task recommendations with readiness assessments."""
    cleaned_id = developer_id.strip()
    verify_developer_ownership(cleaned_id, current_user)
    try:
        recs = task_engine.generate_tasks(
            developer_id=cleaned_id,
            target_role=target_role,
            limit=limit,
        )
        if not recs and task_engine.intelligence_repo is not None:
            existing_tasks = task_engine.intelligence_repo.get_tasks_for_developer(
                cleaned_id, limit=limit
            )
            recs = [
                TaskRecommendation(
                    task=t,
                    importance_score=1.0,
                    readiness_assessment=f"Active pending practice task for {t.target_skill}",
                )
                for t in existing_tasks
            ]
        return recs
    except Exception as err:
        logger.exception("Failed to retrieve recommendations for %s", cleaned_id)
        raise HTTPException(
            status_code=500,
            detail="Internal server error retrieving task recommendations",
        ) from err


@router.get("/{task_id}", response_model=PersonalizedTask)
async def get_task(
    task_id: str,
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> PersonalizedTask:
    """Retrieve an individual personalized task by ID."""
    task = task_engine.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    verify_developer_ownership(task.developer_id, current_user)
    return task


@router.patch("/{task_id}/status", response_model=PersonalizedTask)
async def update_task_status(
    task_id: str,
    request: UpdateTaskStatusRequest,
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> PersonalizedTask:
    """Update progress status and notes for a task."""
    task = task_engine.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    verify_developer_ownership(task.developer_id, current_user)
    try:
        return task_engine.update_task_status(
            task_id=task_id,
            new_status=request.status.value,
            notes=request.notes,
        )
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    except Exception as err:
        logger.exception("Failed to update status for task %s", task_id)
        raise HTTPException(
            status_code=500,
            detail="Internal server error updating task status",
        ) from err


@router.post("/{task_id}/evaluate", response_model=TaskEvaluation)
async def evaluate_task(
    task_id: str,
    request: EvaluateTaskRequest,
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> TaskEvaluation:
    """Evaluate task completion, record outcome, and generate verifiable skill evidence."""
    task = task_engine.get_task(task_id)
    if task:
        verify_developer_ownership(task.developer_id, current_user)
    verify_developer_ownership(request.developer_id, current_user)
    try:
        return task_engine.evaluate_task_completion(
            task_id=task_id,
            success=request.passed,
            execution_notes=request.execution_notes,
            artifacts=request.verified_artifacts,
        )
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    except Exception as err:
        logger.exception("Failed to evaluate task %s", task_id)
        raise HTTPException(
            status_code=500, detail="Internal server error evaluating task completion"
        ) from err


@router.post("/{task_id}/assign", response_model=PersonalizedTask)
async def assign_task(
    task_id: str,
    request: AssignTaskRequest,
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> PersonalizedTask:
    """Accept and assign a personalized task to the developer."""
    task = task_engine.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    verify_developer_ownership(task.developer_id, current_user)
    verify_developer_ownership(request.developer_id, current_user)
    try:
        return task_engine.update_task_status(
            task_id=task_id,
            new_status=TaskStatus.ACCEPTED.value,
            notes=f"Assigned to {request.developer_id}",
        )
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err


@router.post("/{task_id}/submit", response_model=TaskSubmission)
async def submit_task(
    task_id: str,
    request: SubmitTaskRequest,
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> TaskSubmission:
    """Submit code, file tree, repository reference, or explanation for an assigned task."""
    task = task_engine.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    verify_developer_ownership(task.developer_id, current_user)
    verify_developer_ownership(request.developer_id, current_user)
    try:
        return evaluation_engine.submit_work(
            task_id=task_id,
            developer_id=request.developer_id,
            submission_type=request.submission_type,
            source_code=request.source_code,
            file_tree=request.file_tree,
            repo_url=request.repo_url,
            explanation=request.explanation,
        )
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    except Exception as err:
        logger.exception("Failed to submit task %s", task_id)
        raise HTTPException(
            status_code=500,
            detail="Internal server error processing task submission",
        ) from err


@router.get("/{task_id}/submissions", response_model=list[TaskSubmission])
async def get_task_submissions(
    task_id: str,
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> list[TaskSubmission]:
    """Retrieve all submissions for a given task."""
    task = task_engine.get_task(task_id)
    if task:
        verify_developer_ownership(task.developer_id, current_user)
    return task_platform_repo.get_submissions_for_task(task_id)


@router.get("/developer/{developer_id}", response_model=list[PersonalizedTask])
async def list_developer_tasks(
    developer_id: str,
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> list[PersonalizedTask]:
    """List all personalized tasks for a developer with optional status filtering."""
    cleaned_id = developer_id.strip()
    verify_developer_ownership(cleaned_id, current_user)
    if task_engine.intelligence_repo is None:
        return []
    return task_engine.intelligence_repo.get_tasks_for_developer(
        developer_id=cleaned_id,
        status=status,
        limit=limit,
        offset=offset,
    )
