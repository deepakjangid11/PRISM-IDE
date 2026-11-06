import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from prism.api.dependencies import (
    adaptive_mentoring_engine,
    guided_learning_service,
    mentoring_engine,
    task_platform_repo,
)
from prism.exceptions.custom_exception import CustomException
from prism.intelligence.models.task_platform_models import (
    MentoringConversation,
    MentoringMessage,
)
from prism.logging.logger import get_logger
from prism.mentoring.models import (
    AdaptiveMentorRequest,
    AdaptiveMentorResponse,
    MentoringEffectiveness,
    MentoringSessionRecord,
    MentorRequest,
    MentorResponse,
)
from prism.security import get_optional_current_user, verify_developer_ownership

logger = get_logger(__name__)

router = APIRouter(prefix="/mentoring", tags=["Mentoring"])


class StartConversationRequest(BaseModel):
    developer_id: str = Field(..., min_length=1)
    task_id: str | None = None
    initial_query: str | None = None


class SendMessageRequest(BaseModel):
    message: str = Field(..., min_length=1)
    requested_level: int | None = Field(default=None, ge=1, le=6)
    allow_solution: bool = False


class DebugRequest(BaseModel):
    error_output: str = Field(..., min_length=1)
    code_snippet: str | None = None


class StartConversationResponse(BaseModel):
    conversation: MentoringConversation
    first_response: MentoringMessage | None = None


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
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> AdaptiveMentorResponse:
    """Submit an adaptive mentoring query with level and strategy personalization."""
    verify_developer_ownership(request.developer_id, current_user)
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
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> StreamingResponse:
    """Stream an adaptive mentoring response via Server-Sent Events (SSE)."""
    verify_developer_ownership(request.developer_id, current_user)

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
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> list[MentoringSessionRecord]:
    """Retrieve historical adaptive mentoring sessions for a developer."""
    cleaned_id = developer_id.strip()
    verify_developer_ownership(cleaned_id, current_user)
    try:
        return adaptive_mentoring_engine.get_session_history(cleaned_id, limit=limit)
    except Exception as err:
        logger.exception("Failed to retrieve mentoring history")
        raise HTTPException(
            status_code=500, detail="Internal server error retrieving mentoring history"
        ) from err


@router.get("/effectiveness/{developer_id}", response_model=MentoringEffectiveness)
async def get_mentoring_effectiveness(
    developer_id: str,
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> MentoringEffectiveness:
    """Retrieve mentoring effectiveness score and strategy breakdown."""
    cleaned_id = developer_id.strip()
    verify_developer_ownership(cleaned_id, current_user)
    try:
        return adaptive_mentoring_engine.get_mentoring_effectiveness(cleaned_id)
    except Exception as err:
        logger.exception("Failed to compute mentoring effectiveness")
        raise HTTPException(
            status_code=500,
            detail="Internal server error computing mentoring effectiveness",
        ) from err


# =========================================================================
# INTERACTIVE GUIDED LEARNING DIALOGUES (6 PROGRESSIVE LEVELS)
# =========================================================================


@router.post("/conversations/start", response_model=StartConversationResponse)
async def start_mentoring_conversation(
    request: StartConversationRequest,
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> StartConversationResponse:
    """Start a task-linked interactive mentoring dialogue with progressive guidance."""
    verify_developer_ownership(request.developer_id, current_user)
    try:
        conv, first_msg = guided_learning_service.start_conversation(
            developer_id=request.developer_id,
            task_id=request.task_id,
            initial_query=request.initial_query,
        )
        return StartConversationResponse(conversation=conv, first_response=first_msg)
    except Exception as err:
        logger.exception("Failed to start mentoring conversation")
        raise HTTPException(
            status_code=500,
            detail="Internal server error starting mentoring conversation",
        ) from err


@router.get("/conversations/{conversation_id}", response_model=MentoringConversation)
async def get_mentoring_conversation(
    conversation_id: str,
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> MentoringConversation:
    """Retrieve mentoring conversation details."""
    conv = guided_learning_service.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(
            status_code=404,
            detail=f"Mentoring conversation '{conversation_id}' not found",
        )
    verify_developer_ownership(conv.developer_id, current_user)
    return conv


@router.get(
    "/conversations/developer/{developer_id}",
    response_model=list[MentoringConversation],
)
async def list_developer_conversations(
    developer_id: str,
    task_id: str | None = None,
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> list[MentoringConversation]:
    """List interactive mentoring conversations for a developer."""
    cleaned_id = developer_id.strip()
    verify_developer_ownership(cleaned_id, current_user)
    return task_platform_repo.get_conversations_for_developer(
        developer_id=cleaned_id, task_id=task_id
    )


@router.post(
    "/conversations/{conversation_id}/message", response_model=MentoringMessage
)
async def send_conversation_message(
    conversation_id: str,
    request: SendMessageRequest,
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> MentoringMessage:
    """Send developer query and receive tailored mentoring response matching requested guidance level."""
    conv = guided_learning_service.get_conversation(conversation_id)
    if conv:
        verify_developer_ownership(conv.developer_id, current_user)
    try:
        return guided_learning_service.send_message(
            conversation_id=conversation_id,
            developer_message=request.message,
            requested_level=request.requested_level,
            allow_solution=request.allow_solution,
        )
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    except Exception as err:
        logger.exception("Failed to process mentoring message in %s", conversation_id)
        raise HTTPException(
            status_code=500,
            detail="Internal server error generating mentor guidance",
        ) from err


@router.get(
    "/conversations/{conversation_id}/history",
    response_model=list[MentoringMessage],
)
async def get_conversation_history(
    conversation_id: str,
    limit: int = Query(default=100, ge=1, le=200),
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> list[MentoringMessage]:
    """Retrieve complete message history for an interactive mentoring dialogue."""
    conv = guided_learning_service.get_conversation(conversation_id)
    if conv:
        verify_developer_ownership(conv.developer_id, current_user)
    return guided_learning_service.get_history(conversation_id, limit=limit)


@router.post("/conversations/{conversation_id}/hint", response_model=MentoringMessage)
async def request_progressive_hint(
    conversation_id: str,
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> MentoringMessage:
    """Request a progressive hint (Level 3) without code spoilers."""
    conv = guided_learning_service.get_conversation(conversation_id)
    if conv:
        verify_developer_ownership(conv.developer_id, current_user)
    try:
        return guided_learning_service.request_hint(conversation_id)
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err


@router.post(
    "/conversations/{conversation_id}/step-by-step",
    response_model=MentoringMessage,
)
async def request_step_by_step_milestones(
    conversation_id: str,
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> MentoringMessage:
    """Request task decomposition into smaller actionable steps (Level 4)."""
    conv = guided_learning_service.get_conversation(conversation_id)
    if conv:
        verify_developer_ownership(conv.developer_id, current_user)
    try:
        return guided_learning_service.request_step_by_step(conversation_id)
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err


@router.post("/conversations/{conversation_id}/debug", response_model=MentoringMessage)
async def request_debug_guidance(
    conversation_id: str,
    request: DebugRequest,
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> MentoringMessage:
    """Diagnose execution failure and guide developer through error understanding (Level 6)."""
    conv = guided_learning_service.get_conversation(conversation_id)
    if conv:
        verify_developer_ownership(conv.developer_id, current_user)
    try:
        return guided_learning_service.request_debug_assistance(
            conversation_id=conversation_id,
            error_output=request.error_output,
            code_snippet=request.code_snippet,
        )
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
