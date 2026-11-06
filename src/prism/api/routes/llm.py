"""FastAPI router for PRISM LLM Intelligence endpoints."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from prism.api.dependencies import get_llm_service
from prism.llm.exceptions import (
    LLMAuthenticationError,
    LLMException,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMValidationError,
)
from prism.llm.schemas import LLMHealthStatus, LLMRequest, LLMResponse
from prism.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/llm", tags=["LLM Intelligence"])


@router.get("/health", response_model=LLMHealthStatus)
async def check_llm_health() -> LLMHealthStatus:
    """Check connectivity and health of the active LLM provider."""
    try:
        service = get_llm_service()
        return await service.health_check()
    except Exception as err:
        logger.exception("LLM health probe failed")
        raise HTTPException(
            status_code=500, detail=f"LLM health probe failed: {err}"
        ) from err


@router.post("/complete", response_model=LLMResponse)
async def complete_chat(request: LLMRequest) -> LLMResponse:
    """Generate a chat completion using the configured LLM provider."""
    service = get_llm_service()
    try:
        return await service.generate(request)
    except LLMAuthenticationError as err:
        logger.warning("LLM authentication failure: %s", err)
        raise HTTPException(status_code=401, detail=str(err)) from err
    except LLMRateLimitError as err:
        logger.warning("LLM rate limit reached: %s", err)
        raise HTTPException(status_code=429, detail=str(err)) from err
    except LLMTimeoutError as err:
        logger.warning("LLM request timeout: %s", err)
        raise HTTPException(status_code=504, detail=str(err)) from err
    except LLMValidationError as err:
        logger.warning("LLM validation error: %s", err)
        raise HTTPException(status_code=400, detail=str(err)) from err
    except LLMException as err:
        logger.exception("LLM service error")
        raise HTTPException(status_code=502, detail=str(err)) from err
    except Exception as err:
        logger.exception("Unexpected error during LLM completion")
        raise HTTPException(
            status_code=500, detail="Internal server error during LLM generation"
        ) from err


@router.post("/complete/stream")
async def complete_chat_stream(request: LLMRequest) -> StreamingResponse:
    """Stream a chat completion using Server-Sent Events (SSE)."""
    service = get_llm_service()

    async def event_generator() -> AsyncIterator[str]:
        try:
            async for chunk in service.generate_stream(request):
                data = chunk.model_dump_json()
                yield f"data: {data}\n\n"
            yield "data: [DONE]\n\n"
        except (LLMException, Exception) as err:
            logger.exception("Error during LLM streaming")
            error_payload = json.dumps({"error": str(err)})
            yield f"data: {error_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
