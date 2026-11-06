import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from prism.api.dependencies import evaluation_engine, task_platform_repo
from prism.intelligence.models.task_platform_models import (
    DetailedTaskEvaluation,
)
from prism.security import get_optional_current_user, verify_developer_ownership

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])


@router.post("/submissions/{submission_id}", response_model=DetailedTaskEvaluation)
async def evaluate_submission(
    submission_id: str,
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> DetailedTaskEvaluation:
    """Evaluate a task submission using static AST analysis and acceptance criteria verification."""
    sub = task_platform_repo.get_submission(submission_id)
    if sub:
        verify_developer_ownership(sub.developer_id, current_user)
    try:
        return evaluation_engine.evaluate_submission(submission_id)
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    except Exception as err:
        logger.exception("Failed to evaluate submission %s", submission_id)
        raise HTTPException(
            status_code=500,
            detail="Internal server error evaluating submission",
        ) from err


@router.get("/{evaluation_id}", response_model=DetailedTaskEvaluation)
async def get_evaluation(
    evaluation_id: str,
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> DetailedTaskEvaluation:
    """Retrieve structured evaluation result by evaluation ID."""
    eval_result = task_platform_repo.get_evaluation(evaluation_id)
    if not eval_result:
        raise HTTPException(
            status_code=404, detail=f"Evaluation '{evaluation_id}' not found"
        )
    verify_developer_ownership(eval_result.developer_id, current_user)
    return eval_result


@router.get(
    "/submissions/{submission_id}/result",
    response_model=DetailedTaskEvaluation,
)
async def get_evaluation_by_submission(
    submission_id: str,
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> DetailedTaskEvaluation:
    """Retrieve evaluation result associated with a specific task submission."""
    eval_result = task_platform_repo.get_evaluation_by_submission(submission_id)
    if not eval_result:
        raise HTTPException(
            status_code=404,
            detail=f"No evaluation result found for submission '{submission_id}'",
        )
    verify_developer_ownership(eval_result.developer_id, current_user)
    return eval_result


@router.get("/developer/{developer_id}", response_model=list[DetailedTaskEvaluation])
async def get_developer_evaluations(
    developer_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> list[DetailedTaskEvaluation]:
    """Retrieve evaluation history for a developer in reverse chronological order."""
    cleaned_id = developer_id.strip()
    verify_developer_ownership(cleaned_id, current_user)
    return task_platform_repo.get_evaluations_for_developer(
        developer_id=cleaned_id, limit=limit, offset=offset
    )
