"""Schemas for Document Chunking, Vector Embeddings, and RAG Retrieval (Phase 20)."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DocumentChunk(BaseModel):
    """An individual text or code fragment extracted from a project file."""

    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    file_path: str
    content: str
    start_line: int = 1
    end_line: int = 1
    chunk_type: str = "code"  # "code", "docstring", "markdown", "config"
    language: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    embedding: list[float] | None = None


class RetrievedChunk(BaseModel):
    """A semantic search result paired with similarity score and citation reference."""

    model_config = ConfigDict(extra="forbid")

    chunk: DocumentChunk
    score: float
    citation: str


class RAGQueryRequest(BaseModel):
    """Request query for semantic code and document retrieval."""

    model_config = ConfigDict(extra="forbid")

    query: str
    project_path: str | None = None
    top_k: int = Field(default=4, ge=1, le=20)
    min_score: float = Field(default=0.0, ge=0.0, le=1.0)
    language: str | None = None


class RAGSearchResult(BaseModel):
    """Result of semantic retrieval containing relevant chunks and timing telemetry."""

    model_config = ConfigDict(extra="forbid")

    query: str
    chunks: list[RetrievedChunk]
    total_retrieved: int
    duration_ms: float
