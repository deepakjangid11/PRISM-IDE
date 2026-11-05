from fastapi import APIRouter, HTTPException, Query, status

from prism.api.dependencies import activity_intelligence_service
from prism.exceptions.custom_exception import CustomException
from prism.intelligence.models.activity_classification_models import (
    ActivityIngestRequest,
    ActivityResponse,
    ActivitySummaryResponse,
    BatchActivityIngestRequest,
    LanguageDistributionItem,
    PaginatedActivityResponse,
)
from prism.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/activity", tags=["Activity Intelligence"])


@router.post(
    "/record",
    response_model=ActivityResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_activity(
    request: ActivityIngestRequest,
) -> ActivityResponse:
    """Ingest, classify, associate session, and persist a developer activity."""
    try:
        return activity_intelligence_service.ingest_activity(request)
    except ValueError as err:
        logger.warning("Activity validation failed: %s", err)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)
        ) from err
    except CustomException as err:
        logger.exception("Storage error ingesting activity")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Storage error ingesting activity",
        ) from err


@router.post(
    "/batch",
    response_model=list[ActivityResponse],
    status_code=status.HTTP_201_CREATED,
)
async def batch_record_activities(
    request: BatchActivityIngestRequest,
) -> list[ActivityResponse]:
    """Ingest a batch of developer activities with high throughput."""
    try:
        return activity_intelligence_service.batch_ingest(request)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)
        ) from err
    except CustomException as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Storage error batch ingesting activities",
        ) from err


@router.get(
    "/history/{developer_id}",
    response_model=PaginatedActivityResponse,
    status_code=status.HTTP_200_OK,
)
async def get_activity_history(
    developer_id: str,
    project_path: str | None = Query(None, description="Optional project path filter"),
    session_id: str | None = Query(None, description="Optional session filter"),
    language: str | None = Query(None, description="Optional language filter"),
    category: str | None = Query(None, description="Optional category filter"),
    limit: int = Query(50, ge=1, le=200, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
) -> PaginatedActivityResponse:
    """Retrieve filtered, paginated activity events for a developer."""
    try:
        return activity_intelligence_service.get_history(
            developer_id=developer_id,
            project_path=project_path,
            session_id=session_id,
            language=language,
            category=category,
            limit=limit,
            offset=offset,
        )
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)
        ) from err


@router.get(
    "/session/{session_id}",
    response_model=list[ActivityResponse],
    status_code=status.HTTP_200_OK,
)
async def get_session_activities(
    session_id: str,
) -> list[ActivityResponse]:
    """Retrieve all activities recorded in a specific working session."""
    return activity_intelligence_service.get_session_activities(session_id)


@router.get(
    "/summary/{developer_id}",
    response_model=ActivitySummaryResponse,
    status_code=status.HTTP_200_OK,
)
async def get_activity_summary(
    developer_id: str,
    project_path: str | None = Query(None, description="Optional project filter"),
    time_window: str = Query(
        "all", description="Time window ('all', 'today', '7d', '30d')"
    ),
) -> ActivitySummaryResponse:
    """Retrieve summarized activity counts and metrics for a developer."""
    return activity_intelligence_service.get_activity_summary(
        developer_id=developer_id,
        project_path=project_path,
        time_window=time_window,
    )


@router.get(
    "/analytics/{developer_id}",
    response_model=ActivitySummaryResponse,
    status_code=status.HTTP_200_OK,
)
async def get_activity_analytics(
    developer_id: str,
    project_path: str | None = Query(None, description="Optional project filter"),
    time_window: str = Query(
        "all", description="Time window ('all', 'today', '7d', '30d')"
    ),
) -> ActivitySummaryResponse:
    """Retrieve rich multidimensional activity analytics for a developer."""
    return activity_intelligence_service.get_activity_summary(
        developer_id=developer_id,
        project_path=project_path,
        time_window=time_window,
    )


@router.get(
    "/languages/{developer_id}",
    response_model=list[LanguageDistributionItem],
    status_code=status.HTTP_200_OK,
)
async def get_language_distribution(
    developer_id: str,
    project_path: str | None = Query(None, description="Optional project filter"),
) -> list[LanguageDistributionItem]:
    """Retrieve programming language activity distribution."""
    return activity_intelligence_service.get_language_distribution(
        developer_id=developer_id, project_path=project_path
    )
