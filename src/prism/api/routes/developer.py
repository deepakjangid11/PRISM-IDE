from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from prism.api.dependencies import (
    behavior_analyzer,
    skill_graph,
    skill_tracker,
)
from prism.exceptions.custom_exception import CustomException
from prism.intelligence.models.developer_behavior_models import (
    DeveloperActivity,
    DeveloperBehaviorInsights,
)
from prism.intelligence.models.skill_models import (
    DeveloperSkill,
    DeveloperSkillProfile,
    SkillEvidence,
    SkillGraphData,
)
from prism.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/developer", tags=["Developer"])


class DeveloperBehaviorRequest(BaseModel):
    activities: list[DeveloperActivity] = Field(default_factory=list)
    developer_id: str | None = None
    project_path: str | None = None


@router.post("/behavior", response_model=DeveloperBehaviorInsights)
async def analyze_behavior(
    request: DeveloperBehaviorRequest,
) -> DeveloperBehaviorInsights:
    """Analyze developer activities and session data to generate behavioral insights."""
    try:
        logger.info("API request: analyze developer behavior")
        return behavior_analyzer.analyze(
            activities=request.activities,
            developer_id=request.developer_id,
            project_path=request.project_path,
        )
    except ValueError as err:
        logger.warning("Validation error in behavior analysis API: %s", err)
        raise HTTPException(status_code=400, detail=str(err)) from err
    except CustomException as err:
        logger.exception("Behavior analysis API failed unexpectedly")
        raise HTTPException(
            status_code=500, detail="Internal server error analyzing behavior"
        ) from err


@router.post("/skills/record", response_model=DeveloperSkill)
async def record_skill_evidence(evidence: SkillEvidence) -> DeveloperSkill:
    """Record concrete evidence for a developer's technical skill."""
    try:
        logger.info(
            "API request: record skill evidence | dev=%s | skill=%s",
            evidence.developer_id,
            evidence.skill_name,
        )
        return skill_tracker.record_evidence(evidence)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    except Exception as err:
        logger.exception("Record skill evidence API failed")
        raise HTTPException(
            status_code=500, detail="Internal server error recording skill evidence"
        ) from err


@router.get("/skills/graph", response_model=SkillGraphData)
async def get_skill_graph() -> SkillGraphData:
    """Retrieve serializable snapshot of the technical skill graph."""
    return skill_graph.export_graph()


@router.get("/skills/{developer_id}", response_model=DeveloperSkillProfile)
async def get_developer_skill_profile(
    developer_id: str,
) -> DeveloperSkillProfile:
    """Retrieve skill profile for a specific developer."""
    try:
        return skill_tracker.get_profile(developer_id)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
