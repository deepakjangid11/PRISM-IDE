"""FastAPI routes for Developer Performance Analytics."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from prism.api.dependencies import performance_analytics
from prism.intelligence.models.developer_intelligence_models import (
    DeveloperPerformanceSnapshot,
)
from prism.intelligence.performance_analytics import (
    LearningProgressAnalytics,
    PerformanceOverview,
    SkillImprovementAnalytics,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Performance Analytics"])


@router.get("/performance/{developer_id}", response_model=PerformanceOverview)
async def get_performance_overview(
    developer_id: str,
) -> PerformanceOverview:
    """Retrieve comprehensive developer performance snapshot and role readiness."""
    try:
        return performance_analytics.get_overview(developer_id)
    except Exception as err:
        logger.exception("Failed to retrieve performance snapshot for %s", developer_id)
        raise HTTPException(
            status_code=500,
            detail="Internal server error retrieving performance snapshot",
        ) from err


@router.get("/improvement/{developer_id}", response_model=SkillImprovementAnalytics)
async def get_skill_improvement(
    developer_id: str,
) -> SkillImprovementAnalytics:
    """Retrieve skill improvement rates and growth metrics."""
    try:
        return performance_analytics.get_skill_improvement(developer_id)
    except Exception as err:
        logger.exception("Failed to retrieve skill improvement for %s", developer_id)
        raise HTTPException(
            status_code=500, detail="Internal server error retrieving skill improvement"
        ) from err


@router.get("/learning/{developer_id}", response_model=LearningProgressAnalytics)
async def get_learning_progress(
    developer_id: str,
) -> LearningProgressAnalytics:
    """Retrieve learning trajectory and consistency metrics."""
    try:
        return performance_analytics.get_learning_progress(developer_id)
    except Exception as err:
        logger.exception("Failed to retrieve learning progress for %s", developer_id)
        raise HTTPException(
            status_code=500, detail="Internal server error retrieving learning progress"
        ) from err


@router.get(
    "/history/{developer_id}", response_model=list[DeveloperPerformanceSnapshot]
)
async def get_historical_snapshots(
    developer_id: str,
    limit: int = Query(default=10, ge=1, le=50),
) -> list[DeveloperPerformanceSnapshot]:
    """Retrieve historical performance snapshots for longitudinal analysis."""
    try:
        return performance_analytics.get_historical_snapshots(developer_id, limit=limit)
    except Exception as err:
        logger.exception("Failed to retrieve performance history for %s", developer_id)
        raise HTTPException(
            status_code=500,
            detail="Internal server error retrieving performance history",
        ) from err
