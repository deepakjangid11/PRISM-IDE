"""Deterministic Mock LLM Provider for testing and offline development (Phase 20)."""

import asyncio
from collections.abc import AsyncIterator, Callable

from prism.llm.base import BaseLLMProvider
from prism.llm.exceptions import LLMException
from prism.llm.schemas import (
    LLMHealthStatus,
    LLMProviderType,
    LLMRequest,
    LLMResponse,
    LLMUsage,
    StreamChunk,
)


class MockLLMProvider(BaseLLMProvider):
    """In-memory mock LLM provider with canned responses and error injection capabilities."""

    def __init__(
        self,
        default_model: str = "mock-mentor-model",
        default_response: str | None = None,
        response_handler: Callable[[LLMRequest], str] | None = None,
    ) -> None:
        self._default_model = default_model
        self._default_response = (
            default_response
            or "This is a deterministic, evidence-grounded response from PRISM Mock LLM."
        )
        self._response_handler = response_handler
        self.recorded_requests: list[LLMRequest] = []
        self.should_fail: bool = False
        self.failure_exception: Exception | None = None
        self.simulated_latency: float = 0.01

    @property
    def provider_type(self) -> LLMProviderType:
        return LLMProviderType.MOCK

    @property
    def default_model(self) -> str:
        return self._default_model

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Return simulated response or trigger configured failure."""
        self.recorded_requests.append(request)

        if self.should_fail:
            if self.failure_exception:
                raise self.failure_exception
            raise LLMException(
                "Simulated Mock LLM failure (rate limit / network error)"
            )

        if self.simulated_latency > 0:
            await asyncio.sleep(self.simulated_latency)

        if self._response_handler:
            content = self._response_handler(request)
        else:
            content = self._default_response

        prompt_len = sum(len(m.content) for m in request.messages)
        usage = LLMUsage(
            prompt_tokens=max(1, prompt_len // 4),
            completion_tokens=max(1, len(content) // 4),
            total_tokens=max(2, (prompt_len + len(content)) // 4),
        )

        return LLMResponse(
            content=content,
            model=request.model or self.default_model,
            provider=self.provider_type.value,
            usage=usage,
            finish_reason="stop",
            latency_seconds=self.simulated_latency,
            correlation_id=request.correlation_id,
        )

    async def generate_stream(self, request: LLMRequest) -> AsyncIterator[StreamChunk]:
        """Yield simulated streaming words."""
        self.recorded_requests.append(request)

        if self.should_fail:
            if self.failure_exception:
                raise self.failure_exception
            raise LLMException("Simulated Mock LLM streaming failure")

        if self._response_handler:
            content = self._response_handler(request)
        else:
            content = self._default_response

        words = content.split(" ")
        for i, word in enumerate(words):
            delta = word if i == 0 else f" {word}"
            yield StreamChunk(
                delta=delta,
                finish_reason="stop" if i == len(words) - 1 else None,
                provider=self.provider_type.value,
                model=request.model or self.default_model,
            )
            await asyncio.sleep(0.005)

    async def health_check(self) -> LLMHealthStatus:
        """Return healthy status unless configured to fail."""
        if self.should_fail:
            return LLMHealthStatus(
                provider=self.provider_type.value,
                status="offline",
                model=self.default_model,
                error="Simulated health check failure",
            )
        return LLMHealthStatus(
            provider=self.provider_type.value,
            status="healthy",
            model=self.default_model,
            latency_ms=1.5,
        )
