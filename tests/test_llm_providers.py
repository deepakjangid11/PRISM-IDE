"""Unit tests for Phase 20 LLM Provider architecture and LLMService."""

from __future__ import annotations

from typing import Self
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from pydantic import BaseModel

from prism.config.settings import Settings
from prism.llm.base import BaseLLMProvider
from prism.llm.exceptions import (
    LLMAuthenticationError,
    LLMException,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMValidationError,
)
from prism.llm.factory import LLMProviderFactory
from prism.llm.providers.base_provider import OpenAICompatibleProvider
from prism.llm.providers.gemini_provider import GeminiProvider
from prism.llm.providers.groq_provider import GroqProvider
from prism.llm.providers.mock_provider import MockLLMProvider
from prism.llm.providers.openai_provider import OpenAIProvider
from prism.llm.schemas import (
    LLMHealthStatus,
    LLMMessage,
    LLMProviderType,
    LLMRequest,
    LLMResponse,
    LLMRole,
)
from prism.llm.service import LLMService


class SampleStructuredOutput(BaseModel):
    title: str
    difficulty: int


@pytest.fixture
def mock_provider() -> MockLLMProvider:
    provider = MockLLMProvider(default_response="Test mock guidance.")
    provider.simulated_latency = 0.0
    return provider


@pytest.fixture
def llm_request() -> LLMRequest:
    return LLMRequest(
        messages=[
            LLMMessage(role=LLMRole.SYSTEM, content="System prompt"),
            LLMMessage(role=LLMRole.USER, content="How do I write async Python?"),
        ]
    )


@pytest.mark.anyio
async def test_mock_provider_generation(
    mock_provider: MockLLMProvider, llm_request: LLMRequest
) -> None:
    res = await mock_provider.generate(llm_request)
    assert isinstance(res, LLMResponse)
    assert res.content == "Test mock guidance."
    assert res.provider == "mock"
    assert res.model == "mock-mentor-model"
    assert res.usage.total_tokens > 0


@pytest.mark.anyio
async def test_mock_provider_streaming(
    mock_provider: MockLLMProvider, llm_request: LLMRequest
) -> None:
    chunks = []
    async for chunk in mock_provider.generate_stream(llm_request):
        chunks.append(chunk.delta)
    full_text = "".join(chunks)
    assert full_text == "Test mock guidance."


@pytest.mark.anyio
async def test_mock_provider_error_injection(llm_request: LLMRequest) -> None:
    provider = MockLLMProvider()
    provider.should_fail = True
    provider.failure_exception = LLMRateLimitError("Mock rate limit exceeded")
    with pytest.raises(LLMRateLimitError, match="Mock rate limit exceeded"):
        await provider.generate(llm_request)


@pytest.mark.anyio
async def test_mock_provider_health_check(mock_provider: MockLLMProvider) -> None:
    status = await mock_provider.health_check()
    assert status.status == "healthy"
    assert status.provider == "mock"
    assert status.latency_ms >= 0.0


@pytest.mark.anyio
async def test_mock_provider_default_failure(llm_request: LLMRequest) -> None:
    provider = MockLLMProvider()
    provider.should_fail = True
    provider.failure_exception = None
    with pytest.raises(LLMException, match="Simulated Mock LLM failure"):
        await provider.generate(llm_request)


@pytest.mark.anyio
async def test_mock_provider_latency_and_response_handler(
    llm_request: LLMRequest,
) -> None:
    provider = MockLLMProvider(
        response_handler=lambda req: "Custom handled: " + req.messages[-1].content
    )
    provider.simulated_latency = 0.001
    res = await provider.generate(llm_request)
    assert res.content == "Custom handled: How do I write async Python?"


@pytest.mark.anyio
async def test_mock_provider_streaming_failures_and_handler(
    llm_request: LLMRequest,
) -> None:
    provider = MockLLMProvider()
    provider.should_fail = True

    # 1. Default streaming failure
    with pytest.raises(LLMException, match="Simulated Mock LLM streaming failure"):
        async for _ in provider.generate_stream(llm_request):
            pass

    # 2. Configured exception streaming failure
    provider.failure_exception = LLMTimeoutError("Stream timed out")
    with pytest.raises(LLMTimeoutError, match="Stream timed out"):
        async for _ in provider.generate_stream(llm_request):
            pass

    # 3. Custom response handler streaming
    provider.should_fail = False
    provider.failure_exception = None
    provider._response_handler = lambda req: "Custom streamed response"
    chunks = []
    async for chunk in provider.generate_stream(llm_request):
        chunks.append(chunk.delta)
    assert "".join(chunks) == "Custom streamed response"


@pytest.mark.anyio
async def test_mock_provider_health_check_failure() -> None:
    provider = MockLLMProvider()
    provider.should_fail = True
    status = await provider.health_check()
    assert status.status == "offline"
    assert "Simulated health check failure" in (status.error or "")


def test_provider_factory_mock() -> None:
    LLMProviderFactory.clear_cache()
    provider = LLMProviderFactory.create_provider(provider_name="mock")
    assert isinstance(provider, MockLLMProvider)


def test_provider_factory_caching() -> None:
    LLMProviderFactory.clear_cache()
    p1 = LLMProviderFactory.create_provider(provider_name="mock")
    p2 = LLMProviderFactory.create_provider(provider_name="mock")
    assert p1 is p2


def test_provider_factory_invalid_type() -> None:
    with pytest.raises(LLMException, match="Unsupported LLM provider"):
        LLMProviderFactory.create_provider(provider_name="unknown_cloud")


def test_provider_factory_custom_registration() -> None:
    class CustomProvider(BaseLLMProvider):
        @property
        def provider_type(self) -> LLMProviderType:
            return LLMProviderType.MOCK

        @property
        def default_model(self) -> str:
            return "custom-v1"

        async def generate(self, request: LLMRequest) -> LLMResponse:
            return LLMResponse(content="Custom", model="custom-v1", provider="custom")

        async def generate_stream(self, request: LLMRequest):
            yield

        async def health_check(self) -> LLMHealthStatus:
            return LLMHealthStatus(
                provider="custom", status="healthy", model="custom-v1"
            )

    inst = CustomProvider()
    LLMProviderFactory.register_provider("custom_type", inst)
    retrieved = LLMProviderFactory.create_provider("custom_type")
    assert retrieved is inst


def test_concrete_providers_initialization() -> None:
    groq = GroqProvider(api_key="gsk_test")
    assert groq.provider_type == LLMProviderType.GROQ
    assert groq.default_model == "llama-3.3-70b-versatile"

    openai = OpenAIProvider(api_key="sk-test")
    assert openai.provider_type == LLMProviderType.OPENAI
    assert openai.default_model == "gpt-4o-mini"

    gemini = GeminiProvider(api_key="AIzaSyTest")
    assert gemini.provider_type == LLMProviderType.GEMINI
    assert gemini.default_model == "gemini-2.5-flash"


@pytest.mark.anyio
async def test_openai_compatible_provider_success() -> None:
    provider = OpenAICompatibleProvider(
        provider_type=LLMProviderType.OPENAI,
        api_key="test-key",
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
    )

    mock_resp = {
        "id": "chatcmpl-123",
        "model": "gpt-4o-mini",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Hello from OpenAI compatible API",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25},
    }

    with patch.object(provider._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = httpx.Response(
            200,
            json=mock_resp,
            request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
        )
        req = LLMRequest(messages=[LLMMessage(role=LLMRole.USER, content="Hello")])
        res = await provider.generate(req)
        assert res.content == "Hello from OpenAI compatible API"
        assert res.usage.total_tokens == 25


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("status_code", "err_type"),
    [
        (401, LLMAuthenticationError),
        (429, LLMRateLimitError),
        (504, LLMTimeoutError),
        (500, LLMProviderError),
    ],
)
async def test_openai_compatible_provider_errors(
    status_code: int, err_type: type[Exception]
) -> None:
    provider = OpenAICompatibleProvider(
        provider_type=LLMProviderType.OPENAI,
        api_key="test-key",
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
    )

    with patch.object(provider._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = httpx.Response(
            status_code,
            text=f"Error {status_code}",
            request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
        )
        req = LLMRequest(messages=[LLMMessage(role=LLMRole.USER, content="Test")])
        with pytest.raises(err_type):
            await provider.generate(req)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("status_code", "err_type"),
    [
        (401, LLMAuthenticationError),
        (429, LLMRateLimitError),
        (504, LLMTimeoutError),
        (500, LLMProviderError),
    ],
)
async def test_openai_compatible_provider_streaming_errors(
    status_code: int, err_type: type[Exception]
) -> None:
    provider = OpenAICompatibleProvider(
        provider_type=LLMProviderType.OPENAI,
        api_key="test-key",
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
    )

    class MockStreamResponse:
        def __init__(self) -> None:
            self.status_code = status_code

        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

        async def aread(self) -> bytes:
            return b"Stream error body"

    with patch.object(provider._client, "stream", return_value=MockStreamResponse()):
        req = LLMRequest(messages=[LLMMessage(role=LLMRole.USER, content="Test")])
        with pytest.raises(err_type):
            async for _ in provider.generate_stream(req):
                pass


@pytest.mark.anyio
async def test_llm_service_retry_resilience() -> None:
    failing_provider = AsyncMock(spec=BaseLLMProvider)
    failing_provider.provider_type = LLMProviderType.MOCK
    failing_provider.default_model = "flaky-model"

    success_resp = LLMResponse(
        content="Success after retry", model="flaky-model", provider="flaky"
    )
    failing_provider.generate.side_effect = [
        LLMRateLimitError("Rate limit exceeded, try again in 1s"),
        LLMTimeoutError("Gateway timed out"),
        success_resp,
    ]

    custom_settings = Settings(
        llm_max_retries=3,
        llm_retry_backoff_factor=1.1,
    )
    service = LLMService(provider=failing_provider, app_settings=custom_settings)

    req = LLMRequest(messages=[LLMMessage(role=LLMRole.USER, content="Retry test")])
    res = await service.complete(req)
    assert res.content == "Success after retry"
    assert failing_provider.generate.call_count == 3


@pytest.mark.anyio
async def test_llm_service_retry_exceeded() -> None:
    failing_provider = AsyncMock(spec=BaseLLMProvider)
    failing_provider.generate.side_effect = LLMTimeoutError(
        "Persistent connection timeout"
    )

    custom_settings = Settings(llm_max_retries=2, llm_retry_backoff_factor=1.1)
    service = LLMService(provider=failing_provider, app_settings=custom_settings)

    req = LLMRequest(messages=[LLMMessage(role=LLMRole.USER, content="Retry test")])
    with pytest.raises(LLMTimeoutError):
        await service.complete(req)


@pytest.mark.anyio
async def test_llm_service_structured_output_json_fence() -> None:
    provider = MockLLMProvider(
        default_response='```json\n{\n  "title": "Async Patterns",\n  "difficulty": 3\n}\n```'
    )
    provider.simulated_latency = 0.0
    service = LLMService(provider=provider)

    req = LLMRequest(messages=[LLMMessage(role=LLMRole.USER, content="Give me task")])
    parsed = await service.complete_structured(req, SampleStructuredOutput)
    assert isinstance(parsed, SampleStructuredOutput)
    assert parsed.title == "Async Patterns"
    assert parsed.difficulty == 3


@pytest.mark.anyio
async def test_llm_service_structured_output_invalid_json() -> None:
    provider = MockLLMProvider(default_response="Not valid JSON at all")
    provider.simulated_latency = 0.0
    service = LLMService(provider=provider)

    req = LLMRequest(messages=[LLMMessage(role=LLMRole.USER, content="Give me task")])
    with pytest.raises(LLMValidationError):
        await service.complete_structured(req, SampleStructuredOutput)


@pytest.mark.anyio
async def test_openai_compatible_streaming() -> None:
    provider = OpenAICompatibleProvider(
        provider_type=LLMProviderType.OPENAI,
        api_key="test-key",
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
    )

    class MockStreamResponse:
        def __init__(self) -> None:
            self.status_code = 200

        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

        async def aiter_lines(self):
            yield 'data: {"choices":[{"delta":{"content":"Hello "},"finish_reason":null}]}'
            yield 'data: {"choices":[{"delta":{"content":"world!"},"finish_reason":"stop"}]}'
            yield "data: [DONE]"

    with patch.object(provider._client, "stream") as mock_stream:
        mock_stream.return_value = MockStreamResponse()
        req = LLMRequest(messages=[LLMMessage(role=LLMRole.USER, content="Hi")])
        chunks = []
        async for chunk in provider.generate_stream(req):
            chunks.append(chunk.delta)
        assert "".join(chunks) == "Hello world!"


@pytest.mark.anyio
async def test_openai_compatible_missing_key() -> None:
    provider = OpenAICompatibleProvider(
        provider_type=LLMProviderType.OPENAI,
        api_key="",
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
    )
    req = LLMRequest(messages=[LLMMessage(role=LLMRole.USER, content="Hi")])
    with pytest.raises(LLMAuthenticationError):
        await provider.generate(req)

    with pytest.raises(LLMAuthenticationError):
        async for _ in provider.generate_stream(req):
            pass

    health = await provider.health_check()
    assert health.status == "offline"


@pytest.mark.anyio
async def test_openai_compatible_network_and_timeout_errors() -> None:
    provider = OpenAICompatibleProvider(
        provider_type=LLMProviderType.OPENAI,
        api_key="valid-key",
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
    )
    req = LLMRequest(messages=[LLMMessage(role=LLMRole.USER, content="Hi")])

    with (
        patch.object(
            provider._client, "post", side_effect=httpx.TimeoutException("Timeout")
        ),
        pytest.raises(LLMTimeoutError),
    ):
        await provider.generate(req)

    with (
        patch.object(
            provider._client, "post", side_effect=httpx.RequestError("Network error")
        ),
        pytest.raises(LLMException),
    ):
        await provider.generate(req)


@pytest.mark.anyio
async def test_openai_compatible_health_and_close() -> None:
    provider = OpenAICompatibleProvider(
        provider_type=LLMProviderType.OPENAI,
        api_key="valid-key",
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
    )
    req = LLMRequest(
        messages=[LLMMessage(role=LLMRole.USER, content="Hi")],
        response_format="json_object",
    )
    payload = provider._prepare_payload(req)
    assert payload["response_format"] == {"type": "json_object"}

    with patch.object(
        provider,
        "generate",
        new_callable=AsyncMock,
        return_value=LLMResponse(
            content="pong", model="gpt-4o-mini", provider="openai"
        ),
    ):
        health = await provider.health_check()
        assert health.status == "healthy"

    await provider.aclose()

    service = LLMService(provider=provider)
    await service.aclose()


@pytest.mark.anyio
async def test_openai_compatible_health_check() -> None:
    provider = OpenAICompatibleProvider(
        provider_type=LLMProviderType.OPENAI,
        api_key="test-key",
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
    )

    with patch.object(provider._client, "post", new_callable=AsyncMock) as mock_post:
        # Healthy
        mock_post.return_value = httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok"}}]},
            request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
        )
        status = await provider.health_check()
        assert status.status == "healthy"

        # Unhealthy
        mock_post.return_value = httpx.Response(
            500,
            text="Internal Error",
            request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
        )
        unhealthy_status = await provider.health_check()
        assert unhealthy_status.status in ("degraded", "offline")


def test_factory_concrete_providers_creation() -> None:
    LLMProviderFactory.clear_cache()
    p_groq = LLMProviderFactory.create_provider("groq", force_new=True)
    assert p_groq.provider_type == LLMProviderType.GROQ

    p_openai = LLMProviderFactory.create_provider("openai", force_new=True)
    assert p_openai.provider_type == LLMProviderType.OPENAI

    p_gemini = LLMProviderFactory.create_provider("gemini", force_new=True)
    assert p_gemini.provider_type == LLMProviderType.GEMINI
