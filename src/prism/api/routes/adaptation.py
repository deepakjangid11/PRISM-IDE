"""FastAPI routes for Learning Adaptation."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from prism.api.dependencies import adaptation_engine
from prism.intelligence.models.developer_intelligence_models import (
    LearningAdaptation,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/adaptation", tags=["Learning Adaptation"])


class AdaptStrategyRequest(BaseModel):
    developer_id: str = Field(..., min_length=1)


@router.post("/adapt", response_model=LearningAdaptation)
async def adapt_learning_strategy(
    request: AdaptStrategyRequest,
) -> LearningAdaptation:
    """Evaluate performance patterns and adapt learning strategy dynamically."""
    try:
        return adaptation_engine.adapt_strategy(request.developer_id)
    except Exception as err:
        logger.exception("Failed to adapt strategy for %s", request.developer_id)
        raise HTTPException(
            status_code=500, detail="Internal server error adapting learning strategy"
        ) from err


@router.get("/strategy/{developer_id}", response_model=LearningAdaptation)
async def get_current_strategy(
    developer_id: str,
) -> LearningAdaptation:
    """Retrieve the currently active learning adaptation strategy."""
    strat = adaptation_engine.get_current_strategy(developer_id)
    if not strat:
        # If no previous adaptation exists, adapt one now dynamically
        strat = adaptation_engine.adapt_strategy(developer_id)
    return strat


@router.get("/history/{developer_id}", response_model=list[LearningAdaptation])
async def get_adaptation_history(
    developer_id: str,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[LearningAdaptation]:
    """Retrieve historical adaptation records for a developer."""
    try:
        return adaptation_engine.get_adaptation_history(developer_id, limit=limit)
    except Exception as err:
        logger.exception("Failed to retrieve adaptation history for %s", developer_id)
        raise HTTPException(
            status_code=500,
            detail="Internal server error retrieving adaptation history",
        ) from err
