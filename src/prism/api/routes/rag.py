"""FastAPI router for PRISM RAG Knowledge Retrieval endpoints."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from prism.api.dependencies import get_rag_service
from prism.logging.logger import get_logger
from prism.rag.schemas import RAGQueryRequest, RAGSearchResult

logger = get_logger(__name__)

router = APIRouter(prefix="/rag", tags=["RAG Code Intelligence"])


class IndexFileRequest(BaseModel):
    """Request payload for indexing an individual code or markdown document."""

    file_path: str = Field(
        ..., min_length=1, description="Path to the source file to chunk and index"
    )
    content: str | None = Field(
        default=None, description="Optional raw content; reads from disk if None"
    )


class IndexProjectRequest(BaseModel):
    """Request payload for scanning and indexing an entire project directory."""

    project_path: str = Field(
        ..., min_length=1, description="Root path of the project to index"
    )


@router.post("/index/file")
async def index_file(request: IndexFileRequest) -> dict[str, Any]:
    """Chunk, embed, and index an individual file into the vector store."""
    service = get_rag_service()
    try:
        count = await service.index_file(
            file_path=request.file_path, content=request.content
        )
        return {
            "status": "indexed",
            "file_path": request.file_path,
            "chunks_indexed": count,
        }
    except FileNotFoundError as err:
        logger.warning("File not found for RAG indexing: %s", err)
        raise HTTPException(status_code=404, detail=str(err)) from err
    except Exception as err:
        logger.exception("Failed to index file into RAG vector store")
        raise HTTPException(
            status_code=500, detail=f"Failed to index file: {err}"
        ) from err


@router.post("/index/project")
async def index_project(request: IndexProjectRequest) -> dict[str, Any]:
    """Scan and index all supported files within a project directory."""
    if not os.path.exists(request.project_path):
        raise HTTPException(
            status_code=404,
            detail=f"Project directory '{request.project_path}' does not exist",
        )
    service = get_rag_service()
    try:
        count = await service.index_project(project_path=request.project_path)
        return {
            "status": "indexed",
            "project_path": request.project_path,
            "total_chunks_indexed": count,
        }
    except FileNotFoundError as err:
        logger.warning("Project path not found for RAG indexing: %s", err)
        raise HTTPException(status_code=404, detail=str(err)) from err
    except Exception as err:
        logger.exception("Failed to index project into RAG store")
        raise HTTPException(
            status_code=500, detail=f"Failed to index project: {err}"
        ) from err


@router.post("/search", response_model=RAGSearchResult)
async def search_rag(request: RAGQueryRequest) -> RAGSearchResult:
    """Retrieve semantically relevant code chunks with citations."""
    service = get_rag_service()
    try:
        return await service.search(request)
    except Exception as err:
        logger.exception("RAG similarity search failed")
        raise HTTPException(
            status_code=500, detail=f"RAG search failed: {err}"
        ) from err


@router.get("/stats")
async def rag_stats() -> dict[str, Any]:
    """Retrieve indexing statistics from the vector store."""
    service = get_rag_service()
    return {
        "total_chunks": service.vector_store.count(),
        "dimension": service.embedding_provider.dimension,
    }


@router.post("/clear")
async def clear_rag() -> dict[str, str]:
    """Clear all indexed documents from the in-memory vector store."""
    service = get_rag_service()
    service.vector_store.clear()
    return {"status": "cleared", "total_chunks": "0"}
