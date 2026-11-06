"""Base HTTP client implementation for OpenAI-compatible LLM endpoints (Phase 20)."""

import json
import time
from collections.abc import AsyncIterator

import httpx

from prism.llm.base import BaseLLMProvider
from prism.llm.exceptions import (
    LLMAuthenticationError,
    LLMException,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from prism.llm.schemas import (
    LLMHealthStatus,
    LLMMessage,
    LLMProviderType,
    LLMRequest,
    LLMResponse,
    LLMRole,
    LLMUsage,
    StreamChunk,
)
from prism.logging.logger import get_logger

logger = get_logger(__name__)


class OpenAICompatibleProvider(BaseLLMProvider):
    """Reusable provider communicating with standard OpenAI-compatible REST APIs."""

    def __init__(
        self,
        provider_type: LLMProviderType,
        api_key: str,
        base_url: str,
        default_model: str,
        timeout_seconds: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._provider_type = provider_type
        self._api_key = api_key.strip()
        self._base_url = base_url.rstrip("/")
        self._default_model = default_model
        self._timeout = timeout_seconds
        self._client = client or httpx.AsyncClient(timeout=timeout_seconds)

    @property
    def provider_type(self) -> LLMProviderType:
        return self._provider_type

    @property
    def default_model(self) -> str:
        return self._default_model

    def _get_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _prepare_payload(
        self, request: LLMRequest, stream: bool = False
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "model": request.model or self.default_model,
            "messages": [
                {"role": m.role.value, "content": m.content} for m in request.messages
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": stream,
        }
        if request.response_format == "json_object":
            payload["response_format"] = {"type": "json_object"}
        return payload

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Execute a non-streaming completion call with timing and error mapping."""
        if not self._api_key:
            raise LLMAuthenticationError(
                f"Missing API key for LLM provider '{self.provider_type.value}'. "
                "Ensure the corresponding API key environment variable is configured."
            )

        endpoint = f"{self._base_url}/chat/completions"
        payload = self._prepare_payload(request, stream=False)
        headers = self._get_headers()

        start_time = time.monotonic()
        logger.info(
            "Dispatching LLM completion request | provider=%s | model=%s | correlation_id=%s",
            self.provider_type.value,
            payload["model"],
            request.correlation_id,
        )

        try:
            response = await self._client.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=self._timeout,
            )
        except httpx.TimeoutException as e:
            logger.error(
                "LLM request timed out after %.1fs | provider=%s",
                self._timeout,
                self.provider_type.value,
            )
            raise LLMTimeoutError(f"LLM request timed out: {e}") from e
        except httpx.RequestError as e:
            logger.error(
                "Network error during LLM request | provider=%s | error=%s",
                self.provider_type.value,
                e,
            )
            raise LLMException(
                f"Network error communicating with LLM provider: {e}"
            ) from e

        latency = round(time.monotonic() - start_time, 3)

        if response.status_code == 401:
            raise LLMAuthenticationError(
                f"Authentication failed for provider '{self.provider_type.value}'. Verify your API key."
            )
        if response.status_code == 429:
            raise LLMRateLimitError(
                f"Rate limit exceeded for provider '{self.provider_type.value}'. Back off and retry later."
            )
        if response.status_code in (408, 504):
            raise LLMTimeoutError(
                f"Gateway timeout (HTTP {response.status_code}) from provider '{self.provider_type.value}'."
            )
        if response.status_code >= 400:
            error_body = response.text[:500]
            logger.error(
                "LLM provider returned HTTP %d | body=%s",
                response.status_code,
                error_body,
            )
            raise LLMProviderError(
                f"LLM provider error (HTTP {response.status_code}): {error_body}"
            )

        data = response.json()
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content", "")
        finish_reason = choice.get("finish_reason", "stop")

        raw_usage = data.get("usage", {})
        usage = LLMUsage(
            prompt_tokens=raw_usage.get("prompt_tokens", 0),
            completion_tokens=raw_usage.get("completion_tokens", 0),
            total_tokens=raw_usage.get("total_tokens", 0),
        )

        logger.info(
            "LLM completion succeeded | provider=%s | model=%s | latency=%.3fs | tokens=%d",
            self.provider_type.value,
            data.get("model", payload["model"]),
            latency,
            usage.total_tokens,
        )

        return LLMResponse(
            content=content,
            model=str(data.get("model", payload["model"])),
            provider=self.provider_type.value,
            usage=usage,
            finish_reason=str(finish_reason),
            latency_seconds=latency,
            correlation_id=request.correlation_id,
        )

    async def generate_stream(self, request: LLMRequest) -> AsyncIterator[StreamChunk]:
        """Stream chunks incrementally using Server-Sent Events (SSE)."""
        if not self._api_key:
            raise LLMAuthenticationError(
                f"Missing API key for LLM provider '{self.provider_type.value}'."
            )

        endpoint = f"{self._base_url}/chat/completions"
        payload = self._prepare_payload(request, stream=True)
        headers = self._get_headers()

        try:
            async with self._client.stream(
                "POST",
                endpoint,
                headers=headers,
                json=payload,
                timeout=self._timeout,
            ) as response:
                if response.status_code == 401:
                    raise LLMAuthenticationError(
                        f"Authentication failed for provider '{self.provider_type.value}'. Verify your API key."
                    )
                if response.status_code == 429:
                    raise LLMRateLimitError(
                        f"Rate limit exceeded for provider '{self.provider_type.value}'. Back off and retry later."
                    )
                if response.status_code in (408, 504):
                    raise LLMTimeoutError(
                        f"Gateway timeout (HTTP {response.status_code}) from provider '{self.provider_type.value}'."
                    )
                if response.status_code >= 400:
                    body = await response.aread()
                    raise LLMProviderError(
                        f"Stream failed (HTTP {response.status_code}): {body.decode(errors='ignore')[:300]}"
                    )

                async for line in response.aiter_lines():
                    clean_line = line.strip()
                    if not clean_line or not clean_line.startswith("data: "):
                        continue
                    data_str = clean_line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk_json = json.loads(data_str)
                        choices = chunk_json.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {}).get("content", "")
                            finish_reason = choices[0].get("finish_reason")
                            if delta:
                                yield StreamChunk(
                                    delta=delta,
                                    finish_reason=finish_reason,
                                    provider=self.provider_type.value,
                                    model=str(
                                        chunk_json.get("model", payload["model"])
                                    ),
                                )
                    except json.JSONDecodeError:
                        continue
        except httpx.TimeoutException as e:
            logger.error(
                "LLM stream timed out after %.1fs | provider=%s",
                self._timeout,
                self.provider_type.value,
            )
            raise LLMTimeoutError(f"LLM streaming timed out: {e}") from e
        except httpx.RequestError as e:
            logger.error(
                "Network error during LLM stream | provider=%s | error=%s",
                self.provider_type.value,
                e,
            )
            raise LLMException(
                f"Network error communicating with LLM provider: {e}"
            ) from e

    async def aclose(self) -> None:
        """Close the underlying HTTP client session."""
        await self._client.aclose()

    close = aclose

    async def health_check(self) -> LLMHealthStatus:
        """Perform lightweight connectivity verification."""
        if not self._api_key:
            return LLMHealthStatus(
                provider=self.provider_type.value,
                status="offline",
                model=self.default_model,
                error="API key not configured",
            )
        start = time.monotonic()
        try:
            ping_req = LLMRequest(
                messages=[LLMMessage(role=LLMRole.USER, content="ping")],
                max_tokens=2,
            )
            await self.generate(ping_req)
            latency = (time.monotonic() - start) * 1000.0
            return LLMHealthStatus(
                provider=self.provider_type.value,
                status="healthy",
                model=self.default_model,
                latency_ms=round(latency, 1),
            )
        except (LLMException, httpx.RequestError) as e:
            latency = (time.monotonic() - start) * 1000.0
            return LLMHealthStatus(
                provider=self.provider_type.value,
                status="degraded",
                model=self.default_model,
                latency_ms=round(latency, 1),
                error=str(e),
            )
