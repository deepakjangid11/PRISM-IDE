import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from prism.api.dependencies import adaptive_mentoring_engine, mentoring_engine
from prism.exceptions.custom_exception import CustomException
from prism.logging.logger import get_logger
from prism.mentoring.models import (
    AdaptiveMentorRequest,
    AdaptiveMentorResponse,
    MentoringEffectiveness,
    MentoringSessionRecord,
    MentorRequest,
    MentorResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/mentoring", tags=["Mentoring"])


@router.post("/request", response_model=MentorResponse)
async def request_mentoring(request: MentorRequest) -> MentorResponse:
    """Submit a mentoring query in Build Mode or Learn Mode."""
    try:
        logger.info(
            "API request: mentoring | dev=%s | mode=%s",
            request.developer_id,
            request.mode.value,
        )
        return mentoring_engine.mentor(request)
    except ValueError as err:
        logger.warning("Mentoring validation error: %s", err)
        raise HTTPException(status_code=400, detail=str(err)) from err
    except CustomException as err:
        logger.exception("Mentoring engine encountered unexpected failure")
        raise HTTPException(
            status_code=500, detail="Internal server error generating mentor response"
        ) from err


@router.post("/adaptive", response_model=AdaptiveMentorResponse)
async def request_adaptive_mentoring(
    request: AdaptiveMentorRequest,
) -> AdaptiveMentorResponse:
    """Submit an adaptive mentoring query with level and strategy personalization."""
    try:
        logger.info(
            "API request: adaptive mentoring | dev=%s | query=%s",
            request.developer_id,
            request.query[:40],
        )
        return await adaptive_mentoring_engine.request_adaptive_mentoring_async(request)
    except ValueError as err:
        logger.warning("Adaptive mentoring validation error: %s", err)
        raise HTTPException(status_code=400, detail=str(err)) from err
    except Exception as err:
        logger.exception("Adaptive mentoring encountered unexpected failure")
        raise HTTPException(
            status_code=500,
            detail="Internal server error generating adaptive mentoring response",
        ) from err


@router.post("/adaptive/stream")
async def stream_adaptive_mentoring(
    request: AdaptiveMentorRequest,
) -> StreamingResponse:
    """Stream an adaptive mentoring response via Server-Sent Events (SSE)."""

    async def event_generator() -> AsyncIterator[str]:
        try:
            async for (
                chunk
            ) in adaptive_mentoring_engine.request_adaptive_mentoring_stream(request):
                data = chunk.model_dump_json()
                yield f"data: {data}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as err:
            logger.exception("Error during adaptive mentoring stream")
            error_payload = json.dumps({"error": str(err)})
            yield f"data: {error_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/history/{developer_id}", response_model=list[MentoringSessionRecord])
async def get_mentoring_history(
    developer_id: str,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[MentoringSessionRecord]:
    """Retrieve historical adaptive mentoring sessions for a developer."""
    try:
        return adaptive_mentoring_engine.get_session_history(developer_id, limit=limit)
    except Exception as err:
        logger.exception("Failed to retrieve mentoring history")
        raise HTTPException(
            status_code=500, detail="Internal server error retrieving mentoring history"
        ) from err


@router.get("/effectiveness/{developer_id}", response_model=MentoringEffectiveness)
async def get_mentoring_effectiveness(
    developer_id: str,
) -> MentoringEffectiveness:
    """Retrieve mentoring effectiveness score and strategy breakdown."""
    try:
        return adaptive_mentoring_engine.get_mentoring_effectiveness(developer_id)
    except Exception as err:
        logger.exception("Failed to compute mentoring effectiveness")
        raise HTTPException(
            status_code=500,
            detail="Internal server error computing mentoring effectiveness",
        ) from err
