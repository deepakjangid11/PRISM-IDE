"""Domain exceptions for LLM provider operations (Phase 20)."""


class LLMException(Exception):
    """Base exception for all LLM provider and service failures."""


class LLMAuthenticationError(LLMException):
    """Raised when an API key is missing or rejected by the provider."""


class LLMRateLimitError(LLMException):
    """Raised when provider rate limits or quotas are exceeded."""


class LLMTimeoutError(LLMException):
    """Raised when an LLM provider request times out."""


class LLMProviderError(LLMException):
    """Raised when an LLM provider returns a 4xx or 5xx error."""


class LLMValidationError(LLMException):
    """Raised when structured response parsing or Pydantic validation fails."""
