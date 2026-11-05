from fastapi import APIRouter, HTTPException, Query, status

from prism.api.dependencies import session_service
from prism.exceptions.custom_exception import CustomException
from prism.intelligence.models.developer_identity_models import (
    DeveloperSession,
    EndSessionRequest,
    HeartbeatRequest,
    SessionHistoryResponse,
    StartSessionRequest,
)

router = APIRouter(prefix="/session", tags=["Session"])


@router.post(
    "/start",
    response_model=DeveloperSession,
    status_code=status.HTTP_201_CREATED,
)
async def start_session(request: StartSessionRequest) -> DeveloperSession:
    """Initiate a new developer working session, concluding any active session."""
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
    "/heartbeat",
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
    "/end",
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
    "/active/{developer_id}",
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
    "/history/{developer_id}",
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
