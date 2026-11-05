from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from prism.api.dependencies import (
    behavior_analyzer,
    identity_service,
    session_service,
    skill_graph,
    skill_tracker,
)
from prism.exceptions.custom_exception import CustomException
from prism.intelligence.models.developer_behavior_models import (
    DeveloperActivity,
    DeveloperBehaviorInsights,
)
from prism.intelligence.models.developer_identity_models import (
    DeveloperIdentificationRequest,
    DeveloperProfile,
    DeveloperRegistrationRequest,
    DeveloperSession,
    DeveloperUpdateRequest,
    EndSessionRequest,
    HeartbeatRequest,
    SessionHistoryResponse,
    StartSessionRequest,
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


# =========================================================================
# DEVELOPER IDENTITY MANAGEMENT ENDPOINTS
# =========================================================================


@router.post(
    "/register",
    response_model=DeveloperProfile,
    status_code=status.HTTP_201_CREATED,
)
async def register_developer(
    request: DeveloperRegistrationRequest,
) -> DeveloperProfile:
    """Register a new developer identity."""
    try:
        return identity_service.register_developer(request)
    except (ValueError, CustomException) as err:
        msg = str(err)
        if "already exists" in msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=msg
            ) from err
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=msg
        ) from err


@router.post(
    "/identify",
    response_model=DeveloperProfile,
    status_code=status.HTTP_200_OK,
)
async def identify_developer(
    request: DeveloperIdentificationRequest,
) -> DeveloperProfile:
    """Resolve an existing developer using developer_id or email."""
    try:
        profile = identity_service.identify_developer(request)
        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Developer identity not found",
            )
        return profile
    except (ValueError, CustomException) as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)
        ) from err


@router.get(
    "/{developer_id}/profile",
    response_model=DeveloperProfile,
    status_code=status.HTTP_200_OK,
)
async def get_developer_profile(developer_id: str) -> DeveloperProfile:
    """Retrieve developer profile attributes by ID."""
    try:
        return identity_service.get_profile(developer_id)
    except (ValueError, CustomException) as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(err)
        ) from err


@router.put(
    "/{developer_id}/profile",
    response_model=DeveloperProfile,
    status_code=status.HTTP_200_OK,
)
async def update_developer_profile(
    developer_id: str, request: DeveloperUpdateRequest
) -> DeveloperProfile:
    """Update permitted developer profile fields."""
    try:
        return identity_service.update_profile(developer_id, request)
    except (ValueError, CustomException) as err:
        msg = str(err)
        if "not found" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=msg
            ) from err
        if "already registered" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=msg
            ) from err
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=msg
        ) from err


# =========================================================================
# DEVELOPER SESSION MANAGEMENT ENDPOINTS
# =========================================================================


@router.post(
    "/session/start",
    response_model=DeveloperSession,
    status_code=status.HTTP_201_CREATED,
)
async def start_session(request: StartSessionRequest) -> DeveloperSession:
    """Initiate a new developer working session, closing any active session."""
    try:
        return session_service.start_session(
            developer_id=request.developer_id,
            project_path=request.project_path,
            metadata=request.metadata,
        )
    except (ValueError, CustomException) as err:
        msg = str(err)
        if "not found" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=msg
            ) from err
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=msg
        ) from err


@router.post(
    "/session/heartbeat",
    response_model=DeveloperSession,
    status_code=status.HTTP_200_OK,
)
async def session_heartbeat(request: HeartbeatRequest) -> DeveloperSession:
    """Touch working session heartbeat and update activity timestamp."""
    try:
        return session_service.send_heartbeat(
            session_id=request.session_id,
            developer_id=request.developer_id,
            metadata=request.metadata,
        )
    except (ValueError, CustomException) as err:
        msg = str(err)
        if "not found" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=msg
            ) from err
        if "does not belong" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=msg
            ) from err
        if "expired" in msg.lower() or "cannot heartbeat" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=msg
            ) from err
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=msg
        ) from err


@router.post(
    "/session/end",
    response_model=DeveloperSession,
    status_code=status.HTTP_200_OK,
)
async def end_session(request: EndSessionRequest) -> DeveloperSession:
    """Conclude an active developer working session."""
    try:
        return session_service.end_session(
            session_id=request.session_id,
            developer_id=request.developer_id,
            status=request.status,
        )
    except (ValueError, CustomException) as err:
        msg = str(err)
        if "not found" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=msg
            ) from err
        if "does not belong" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=msg
            ) from err
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=msg
        ) from err


@router.get(
    "/session/active/{developer_id}",
    response_model=DeveloperSession,
    status_code=status.HTTP_200_OK,
)
async def get_active_session(developer_id: str) -> DeveloperSession:
    """Retrieve the current active working session for a developer."""
    session = session_service.get_active_session(developer_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active session found for developer '{developer_id}'",
        )
    return session


@router.get(
    "/session/history/{developer_id}",
    response_model=SessionHistoryResponse,
    status_code=status.HTTP_200_OK,
)
async def get_session_history(
    developer_id: str,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> SessionHistoryResponse:
    """Fetch paginated working session history for a developer."""
    try:
        return session_service.get_session_history(
            developer_id=developer_id,
            limit=limit,
            offset=offset,
        )
    except (ValueError, CustomException) as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)
        ) from err
