"""FastAPI routes for Intelligent Feedback."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from prism.api.dependencies import feedback_engine
from prism.intelligence.models.developer_intelligence_models import DeveloperFeedback

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["Intelligent Feedback"])


class GenerateFeedbackRequest(BaseModel):
    developer_id: str = Field(..., min_length=1)


@router.get("/{developer_id}", response_model=list[DeveloperFeedback])
async def get_proactive_feedback(developer_id: str) -> list[DeveloperFeedback]:
    """Generate and return proactive diagnostic and coaching feedback."""
    try:
        return feedback_engine.generate_proactive_feedback(developer_id)
    except Exception as err:
        logger.exception("Failed to generate feedback for %s", developer_id)
        raise HTTPException(
            status_code=500,
            detail="Internal server error generating proactive feedback",
        ) from err


@router.post("/generate", response_model=list[DeveloperFeedback])
async def trigger_feedback_generation(
    request: GenerateFeedbackRequest,
) -> list[DeveloperFeedback]:
    """Explicitly trigger proactive coaching feedback for a developer."""
    try:
        return feedback_engine.generate_proactive_feedback(request.developer_id)
    except Exception as err:
        logger.exception("Failed to trigger feedback for %s", request.developer_id)
        raise HTTPException(
            status_code=500, detail="Internal server error triggering feedback"
        ) from err


@router.get("/history/{developer_id}", response_model=list[DeveloperFeedback])
async def get_feedback_history(
    developer_id: str,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[DeveloperFeedback]:
    """Retrieve historical coaching and evaluation feedback delivered to a developer."""
    try:
        return feedback_engine.get_feedback_history(developer_id, limit=limit)
    except Exception as err:
        logger.exception("Failed to retrieve feedback history for %s", developer_id)
        raise HTTPException(
            status_code=500, detail="Internal server error retrieving feedback history"
        ) from err
