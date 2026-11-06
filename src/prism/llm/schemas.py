"""Strongly typed Pydantic V2 schemas for LLM provider integration (Phase 20)."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LLMRole(StrEnum):
    """Roles for messages exchanged with LLM providers."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class LLMProviderType(StrEnum):
    """Supported LLM providers."""

    GROQ = "groq"
    OPENAI = "openai"
    GEMINI = "gemini"
    MOCK = "mock"


class LLMMessage(BaseModel):
    """Single message in a conversational or prompt exchange."""

    model_config = ConfigDict(extra="forbid")

    role: LLMRole
    content: str
    name: str | None = None


class LLMRequest(BaseModel):
    """Request payload sent to an LLM provider."""

    model_config = ConfigDict(extra="forbid")

    messages: list[LLMMessage]
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1, le=8192)
    model: str | None = None
    stream: bool = False
    response_format: str | None = None  # e.g. "json_object"
    correlation_id: str | None = None


class LLMUsage(BaseModel):
    """Token consumption telemetry."""

    model_config = ConfigDict(extra="forbid")

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class LLMResponse(BaseModel):
    """Complete generated response from an LLM provider."""

    model_config = ConfigDict(extra="forbid")

    content: str
    model: str
    provider: str
    usage: LLMUsage = Field(default_factory=LLMUsage)
    finish_reason: str = "stop"
    latency_seconds: float = 0.0
    correlation_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class StreamChunk(BaseModel):
    """Single incremental delta emitted during response streaming."""

    model_config = ConfigDict(extra="forbid")

    delta: str
    finish_reason: str | None = None
    provider: str = ""
    model: str = ""


class LLMHealthStatus(BaseModel):
    """Health check outcome for an LLM provider."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    status: str  # "healthy", "degraded", "offline"
    model: str
    latency_ms: float = 0.0
    error: str | None = None
