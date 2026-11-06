"""FastAPI routes for Developer Performance Analytics."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from prism.api.dependencies import performance_analytics
from prism.intelligence.models.developer_intelligence_models import (
    DeveloperPerformanceSnapshot,
)
from prism.intelligence.performance_analytics import (
    LearningProgressAnalytics,
    PerformanceOverview,
    SkillImprovementAnalytics,
)
from prism.security import get_optional_current_user, verify_developer_ownership

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Performance Analytics"])


@router.get("/performance/{developer_id}", response_model=PerformanceOverview)
async def get_performance_overview(
    developer_id: str,
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> PerformanceOverview:
    """Retrieve comprehensive developer performance snapshot and role readiness."""
    cleaned_id = developer_id.strip()
    verify_developer_ownership(cleaned_id, current_user)
    try:
        return performance_analytics.get_overview(cleaned_id)
    except Exception as err:
        logger.exception("Failed to retrieve performance snapshot for %s", cleaned_id)
        raise HTTPException(
            status_code=500,
            detail="Internal server error retrieving performance snapshot",
        ) from err


@router.get("/improvement/{developer_id}", response_model=SkillImprovementAnalytics)
async def get_skill_improvement(
    developer_id: str,
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> SkillImprovementAnalytics:
    """Retrieve skill improvement rates and growth metrics."""
    cleaned_id = developer_id.strip()
    verify_developer_ownership(cleaned_id, current_user)
    try:
        return performance_analytics.get_skill_improvement(cleaned_id)
    except Exception as err:
        logger.exception("Failed to retrieve skill improvement for %s", cleaned_id)
        raise HTTPException(
            status_code=500, detail="Internal server error retrieving skill improvement"
        ) from err


@router.get("/learning/{developer_id}", response_model=LearningProgressAnalytics)
async def get_learning_progress(
    developer_id: str,
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> LearningProgressAnalytics:
    """Retrieve learning trajectory and consistency metrics."""
    cleaned_id = developer_id.strip()
    verify_developer_ownership(cleaned_id, current_user)
    try:
        return performance_analytics.get_learning_progress(cleaned_id)
    except Exception as err:
        logger.exception("Failed to retrieve learning progress for %s", cleaned_id)
        raise HTTPException(
            status_code=500, detail="Internal server error retrieving learning progress"
        ) from err


@router.get(
    "/history/{developer_id}", response_model=list[DeveloperPerformanceSnapshot]
)
async def get_historical_snapshots(
    developer_id: str,
    limit: int = Query(default=10, ge=1, le=50),
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> list[DeveloperPerformanceSnapshot]:
    """Retrieve historical performance snapshots for longitudinal analysis."""
    cleaned_id = developer_id.strip()
    verify_developer_ownership(cleaned_id, current_user)
    try:
        return performance_analytics.get_historical_snapshots(cleaned_id, limit=limit)
    except Exception as err:
        logger.exception("Failed to retrieve performance history for %s", cleaned_id)
        raise HTTPException(
            status_code=500,
            detail="Internal server error retrieving performance history",
        ) from err
