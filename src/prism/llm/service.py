"""Central LLM Service providing resilience, retries, and structured validation (Phase 20)."""

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from prism.config.settings import Settings
from prism.config.settings import settings as global_settings
from prism.llm.base import BaseLLMProvider
from prism.llm.exceptions import LLMException, LLMValidationError
from prism.llm.factory import LLMProviderFactory
from prism.llm.schemas import (
    LLMHealthStatus,
    LLMRequest,
    LLMResponse,
    StreamChunk,
)
from prism.logging.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMService:
    """Central service managing LLM request lifecycles, retries, and structured parsing."""

    def __init__(
        self,
        provider: BaseLLMProvider | None = None,
        fallback_provider: BaseLLMProvider | None = None,
        app_settings: Settings | None = None,
    ) -> None:
        self.settings = app_settings or global_settings
        self.provider = provider or LLMProviderFactory.create_provider(
            app_settings=self.settings
        )
        self.fallback_provider = fallback_provider

    def set_provider(self, provider: BaseLLMProvider) -> None:
        """Switch active provider instance dynamically."""
        self.provider = provider

    def set_fallback_provider(self, provider: BaseLLMProvider | None) -> None:
        """Set or update secondary fallback provider."""
        self.fallback_provider = provider

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Execute a completion with exponential backoff retries for transient errors and graceful fallback."""
        correlation_id = request.correlation_id or f"llm_{uuid.uuid4().hex[:10]}"
        request_copy = request.model_copy(update={"correlation_id": correlation_id})

        max_retries = self.settings.llm_max_retries
        backoff_factor = self.settings.llm_retry_backoff_factor
        attempt = 0

        while True:
            attempt += 1
            try:
                response = await self.provider.generate(request_copy)
                return response
            except LLMException as e:
                is_transient = any(
                    phrase in str(e).lower()
                    for phrase in (
                        "rate limit",
                        "timeout",
                        "timed out",
                        "503",
                        "502",
                        "network",
                    )
                )
                if not is_transient or attempt > max_retries:
                    logger.error(
                        "LLM completion permanently failed on primary provider '%s' | attempt=%d/%d | correlation_id=%s | error=%s",
                        self.provider.provider_type.value,
                        attempt,
                        max_retries,
                        correlation_id,
                        e,
                    )
                    # Attempt graceful fallback if configured
                    if self.fallback_provider:
                        logger.warning(
                            "Attempting graceful fallback from '%s' to '%s' | correlation_id=%s",
                            self.provider.provider_type.value,
                            self.fallback_provider.provider_type.value,
                            correlation_id,
                        )
                        try:
                            fallback_resp = await self.fallback_provider.generate(
                                request_copy
                            )
                            return fallback_resp
                        except Exception as fb_err:  # noqa: BLE001
                            logger.error(
                                "Fallback provider '%s' also failed | error=%s",
                                self.fallback_provider.provider_type.value,
                                fb_err,
                            )
                    raise

                sleep_time = backoff_factor ** (attempt - 1)
                logger.warning(
                    "LLM transient error encountered | attempt=%d/%d | backoff=%.2fs | error=%s",
                    attempt,
                    max_retries,
                    sleep_time,
                    e,
                )
                await asyncio.sleep(sleep_time)

    async def complete_stream(self, request: LLMRequest) -> AsyncIterator[StreamChunk]:
        """Stream chunks incrementally from the active provider."""
        correlation_id = request.correlation_id or f"llm_str_{uuid.uuid4().hex[:10]}"
        request_copy = request.model_copy(
            update={"correlation_id": correlation_id, "stream": True}
        )

        try:
            async for chunk in self.provider.generate_stream(request_copy):
                yield chunk
        except LLMException:
            raise
        except Exception as e:
            logger.error(
                "Streaming error | correlation_id=%s | error=%s", correlation_id, e
            )
            raise LLMException(f"Streaming failed: {e}") from e

    async def complete_structured(
        self,
        request: LLMRequest,
        response_model: type[T],
    ) -> T:
        """Generate response and parse into a validated Pydantic model."""
        req = request.model_copy(update={"response_format": "json_object"})
        raw_response = await self.complete(req)

        clean_text = raw_response.content.strip()
        clean_text = clean_text.removeprefix("```json").removeprefix("```")
        clean_text = clean_text.removesuffix("```").strip()

        try:
            data = json.loads(clean_text)
            return response_model.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as err:
            logger.error(
                "Structured validation failed on LLM output | error=%s | raw_output=%s",
                err,
                clean_text[:200],
            )
            raise LLMValidationError(
                f"Failed to validate LLM response into {response_model.__name__}: {err}"
            ) from err

    async def health_check(self) -> LLMHealthStatus:
        """Query health status of the active provider."""
        return await self.provider.health_check()

    async def aclose(self) -> None:
        """Close provider resources if supported."""
        if hasattr(self.provider, "aclose"):
            await self.provider.aclose()
        elif hasattr(self.provider, "close"):
            self.provider.close()

    close = aclose

    # Aliases for provider-style interface compatibility
    generate = complete
    generate_stream = complete_stream
