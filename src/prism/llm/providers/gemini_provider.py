"""Google Gemini LLM Provider Adapter (Phase 20)."""

import httpx

from prism.llm.providers.base_provider import OpenAICompatibleProvider
from prism.llm.schemas import LLMProviderType


class GeminiProvider(OpenAICompatibleProvider):
    """Adapter for Google Gemini using its OpenAI-compatible v1beta API."""

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai",
        timeout_seconds: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(
            provider_type=LLMProviderType.GEMINI,
            api_key=api_key,
            base_url=base_url,
            default_model=model or "gemini-2.5-flash",
            timeout_seconds=timeout_seconds,
            client=client,
        )
