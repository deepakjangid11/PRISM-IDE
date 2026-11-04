from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from prism.api.dependencies import (
    gap_analyzer,
    path_generator,
    rec_engine,
    skill_tracker,
)
from prism.learning.models import (
    KnowledgeGap,
    LearningPath,
    LearningRecommendation,
)
from prism.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/learning", tags=["Learning"])


class KnowledgeGapRequest(BaseModel):
    developer_id: str = Field(min_length=1)
    target_skill: str = Field(min_length=1)


class LearningPathRequest(BaseModel):
    developer_id: str = Field(min_length=1)
    target_goal: str = Field(min_length=1)


@router.post("/gaps", response_model=list[KnowledgeGap])
async def identify_knowledge_gaps(
    request: KnowledgeGapRequest,
) -> list[KnowledgeGap]:
    """Identify missing prerequisites and skills with insufficient evidence."""
    try:
        profile = skill_tracker.get_profile(request.developer_id)
        return gap_analyzer.identify_gaps(profile, request.target_skill)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err


@router.post("/paths", response_model=LearningPath)
async def generate_learning_path(
    request: LearningPathRequest,
) -> LearningPath:
    """Generate an ordered, prerequisite-respecting learning path."""
    try:
        profile = skill_tracker.get_profile(request.developer_id)
        return path_generator.generate_path(profile, request.target_goal)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err


@router.post("/recommendations", response_model=list[LearningRecommendation])
async def get_learning_recommendations(
    request: KnowledgeGapRequest,
) -> list[LearningRecommendation]:
    """Generate prioritized, deduplicated learning recommendations."""
    try:
        profile = skill_tracker.get_profile(request.developer_id)
        gaps = gap_analyzer.identify_gaps(profile, request.target_skill)
        return rec_engine.generate_recommendations(profile, gaps)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
