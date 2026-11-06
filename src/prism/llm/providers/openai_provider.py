"""OpenAI LLM Provider Adapter (Phase 20)."""

import httpx

from prism.llm.providers.base_provider import OpenAICompatibleProvider
from prism.llm.schemas import LLMProviderType


class OpenAIProvider(OpenAICompatibleProvider):
    """Adapter for OpenAI API endpoints."""

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(
            provider_type=LLMProviderType.OPENAI,
            api_key=api_key,
            base_url=base_url,
            default_model=model or "gpt-4o-mini",
            timeout_seconds=timeout_seconds,
            client=client,
        )
