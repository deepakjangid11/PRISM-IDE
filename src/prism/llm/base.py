"""Abstract base interface for LLM providers (Phase 20)."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from prism.llm.schemas import (
    LLMHealthStatus,
    LLMProviderType,
    LLMRequest,
    LLMResponse,
    StreamChunk,
)


class BaseLLMProvider(ABC):
    """Abstract interface defining required provider capabilities."""

    @property
    @abstractmethod
    def provider_type(self) -> LLMProviderType:
        """Return the unique provider type enum."""

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Return the default model name if none is explicitly specified in the request."""

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a complete text or structured response asynchronously."""

    @abstractmethod
    def generate_stream(self, request: LLMRequest) -> AsyncIterator[StreamChunk]:
        """Stream response chunks incrementally as they arrive."""

    @abstractmethod
    async def health_check(self) -> LLMHealthStatus:
        """Perform a lightweight connectivity and credential verification probe."""
