"""Groq LLM Provider Adapter (Phase 20)."""

import httpx

from prism.llm.providers.base_provider import OpenAICompatibleProvider
from prism.llm.schemas import LLMProviderType


class GroqProvider(OpenAICompatibleProvider):
    """Adapter for Groq's high-speed LPU inference API."""

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
        base_url: str = "https://api.groq.com/openai/v1",
        timeout_seconds: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(
            provider_type=LLMProviderType.GROQ,
            api_key=api_key,
            base_url=base_url,
            default_model=model or "llama-3.3-70b-versatile",
            timeout_seconds=timeout_seconds,
            client=client,
        )
