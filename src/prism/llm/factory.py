"""Factory for creating and configuring LLM providers (Phase 20)."""

from typing import ClassVar

from prism.config.settings import Settings
from prism.config.settings import settings as global_settings
from prism.llm.base import BaseLLMProvider
from prism.llm.exceptions import LLMException
from prism.llm.providers import (
    GeminiProvider,
    GroqProvider,
    MockLLMProvider,
    OpenAIProvider,
)
from prism.llm.schemas import LLMProviderType
from prism.logging.logger import get_logger

logger = get_logger(__name__)


class LLMProviderFactory:
    """Factory creating provider instances according to configuration."""

    _instances: ClassVar[dict[str, BaseLLMProvider]] = {}

    @classmethod
    def create_provider(
        cls,
        provider_name: str | None = None,
        app_settings: Settings | None = None,
        force_new: bool = False,
    ) -> BaseLLMProvider:
        """Create or return a cached provider instance."""
        cfg = app_settings or global_settings
        target = (provider_name or cfg.llm_provider).strip().lower()

        if not force_new and target in cls._instances:
            return cls._instances[target]

        logger.info("Initializing LLM provider adapter | provider=%s", target)

        provider: BaseLLMProvider
        if target == LLMProviderType.MOCK.value:
            provider = MockLLMProvider(default_model=cfg.llm_model or "mock-model")

        elif target == LLMProviderType.GROQ.value:
            if not cfg.groq_api_key:
                logger.warning("GROQ_API_KEY is not set in environment")
            provider = GroqProvider(
                api_key=cfg.groq_api_key,
                model=cfg.llm_model or None,
                timeout_seconds=cfg.llm_timeout_seconds,
            )

        elif target == LLMProviderType.OPENAI.value:
            if not cfg.openai_api_key:
                logger.warning("OPENAI_API_KEY is not set in environment")
            provider = OpenAIProvider(
                api_key=cfg.openai_api_key,
                model=cfg.llm_model or None,
                timeout_seconds=cfg.llm_timeout_seconds,
            )

        elif target == LLMProviderType.GEMINI.value:
            if not cfg.gemini_api_key:
                logger.warning("GEMINI_API_KEY is not set in environment")
            provider = GeminiProvider(
                api_key=cfg.gemini_api_key,
                model=cfg.llm_model or None,
                timeout_seconds=cfg.llm_timeout_seconds,
            )

        else:
            raise LLMException(
                f"Unsupported LLM provider '{target}'. "
                "Supported options are: 'mock', 'groq', 'openai', 'gemini'."
            )

        cls._instances[target] = provider
        return provider

    @classmethod
    def register_provider(cls, name: str, provider: BaseLLMProvider) -> None:
        """Register a custom or test mock provider."""
        cls._instances[name.strip().lower()] = provider

    @classmethod
    def clear_cache(cls) -> None:
        """Clear cached provider instances."""
        cls._instances.clear()
