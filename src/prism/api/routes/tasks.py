"""FastAPI routes for Personalized Task Recommendations."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from prism.api.dependencies import task_engine
from prism.intelligence.models.developer_intelligence_models import (
    PersonalizedTask,
    TaskEvaluation,
    TaskRecommendation,
    TaskStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["Personalized Tasks"])


class GenerateTasksRequest(BaseModel):
    developer_id: str = Field(..., min_length=1)
    target_role: str | None = None
    limit: int = Field(default=5, ge=1, le=20)


class UpdateTaskStatusRequest(BaseModel):
    status: TaskStatus
    notes: str | None = None


class EvaluateTaskRequest(BaseModel):
    developer_id: str = Field(..., min_length=1)
    passed: bool
    score: float = Field(..., ge=0.0, le=1.0)
    execution_notes: str = ""
    verified_artifacts: list[str] = Field(default_factory=list)


@router.post("/generate", response_model=list[PersonalizedTask])
async def generate_tasks(
    request: GenerateTasksRequest,
) -> list[PersonalizedTask]:
    """Generate targeted, gap-closing personalized tasks for a developer."""
    try:
        recommendations = task_engine.generate_tasks(
            developer_id=request.developer_id,
            target_role=request.target_role,
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
) -> list[TaskRecommendation]:
    """Retrieve prioritized task recommendations with readiness assessments."""
    try:
        recs = task_engine.generate_tasks(
            developer_id=developer_id,
            target_role=target_role,
            limit=limit,
        )
        if not recs and task_engine.intelligence_repo is not None:
            existing_tasks = task_engine.intelligence_repo.get_tasks_for_developer(
                developer_id, limit=limit
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
        logger.exception("Failed to retrieve recommendations for %s", developer_id)
        raise HTTPException(
            status_code=500,
            detail="Internal server error retrieving task recommendations",
        ) from err


@router.get("/{task_id}", response_model=PersonalizedTask)
async def get_task(task_id: str) -> PersonalizedTask:
    """Retrieve an individual personalized task by ID."""
    task = task_engine.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return task


@router.patch("/{task_id}/status", response_model=PersonalizedTask)
async def update_task_status(
    task_id: str,
    request: UpdateTaskStatusRequest,
) -> PersonalizedTask:
    """Update progress status and notes for a task."""
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
) -> TaskEvaluation:
    """Evaluate task completion, record outcome, and generate verifiable skill evidence."""
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
