"""FastAPI routes for Developer Intelligence and Orchestration."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from prism.api.dependencies import (
    intelligence_engine,
    intelligence_orchestrator,
)
from prism.intelligence.models.developer_behavior_models import DeveloperActivity
from prism.intelligence.models.developer_intelligence_models import (
    DeveloperInsight,
    DeveloperIntelligenceProfile,
    IntelligenceAnalysisResult,
    SkillTrend,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/intelligence", tags=["Developer Intelligence"])


class RefreshIntelligenceRequest(BaseModel):
    developer_id: str = Field(..., min_length=1)


class SyncIntelligenceRequest(BaseModel):
    developer_id: str = Field(..., min_length=1)
    target_role: str | None = None


@router.get("/profile/{developer_id}", response_model=DeveloperIntelligenceProfile)
async def get_developer_profile(developer_id: str) -> DeveloperIntelligenceProfile:
    """Retrieve comprehensive developer intelligence profile."""
    try:
        return intelligence_engine.get_profile(developer_id)
    except Exception as err:
        logger.exception("Failed to retrieve profile for %s", developer_id)
        raise HTTPException(
            status_code=500,
            detail="Internal server error retrieving intelligence profile",
        ) from err


@router.get("/insights/{developer_id}", response_model=list[DeveloperInsight])
async def get_developer_insights(
    developer_id: str,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[DeveloperInsight]:
    """Retrieve high-confidence insights generated for a developer."""
    try:
        return intelligence_engine.get_insights(developer_id, limit=limit)
    except Exception as err:
        logger.exception("Failed to retrieve insights for %s", developer_id)
        raise HTTPException(
            status_code=500, detail="Internal server error retrieving insights"
        ) from err


@router.get("/trends/{developer_id}", response_model=list[SkillTrend])
async def get_skill_trends(developer_id: str) -> list[SkillTrend]:
    """Retrieve skill progression trajectories and velocity trends."""
    try:
        return intelligence_engine.get_skill_trends(developer_id)
    except Exception as err:
        logger.exception("Failed to retrieve skill trends for %s", developer_id)
        raise HTTPException(
            status_code=500, detail="Internal server error retrieving skill trends"
        ) from err


@router.post("/refresh", response_model=IntelligenceAnalysisResult)
async def refresh_developer_intelligence(
    request: RefreshIntelligenceRequest,
) -> IntelligenceAnalysisResult:
    """Trigger an on-demand intelligence analysis and snapshot creation."""
    try:
        return intelligence_engine.analyze_developer(request.developer_id)
    except Exception as err:
        logger.exception(
            "Failed to analyze developer intelligence for %s", request.developer_id
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error performing intelligence refresh",
        ) from err


@router.post("/orchestrate/activity")
async def orchestrate_activity(
    activity: DeveloperActivity,
    auto_generate_tasks: bool = Query(default=False),
) -> dict[str, Any]:
    """Ingest activity and execute end-to-end multi-module recalibration."""
    try:
        return intelligence_orchestrator.process_activity_and_recalibrate(
            activity,
            auto_generate_tasks=auto_generate_tasks,
        )
    except Exception as err:
        logger.exception("Failed to orchestrate activity %s", activity.event_id)
        raise HTTPException(
            status_code=500, detail="Internal server error orchestrating activity"
        ) from err


@router.post("/orchestrate/sync")
async def orchestrate_sync(
    request: SyncIntelligenceRequest,
) -> dict[str, Any]:
    """Execute complete multi-module synchronization across all subsystems."""
    try:
        return intelligence_orchestrator.run_full_developer_sync(
            developer_id=request.developer_id,
            target_role=request.target_role,
        )
    except Exception as err:
        logger.exception(
            "Failed to run full developer sync for %s", request.developer_id
        )
        raise HTTPException(
            status_code=500, detail="Internal server error executing full sync"
        ) from err
