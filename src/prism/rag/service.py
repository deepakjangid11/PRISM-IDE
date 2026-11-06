"""High-level RAG Service coordinating chunking, embeddings, and retrieval (Phase 20)."""

import time
from pathlib import Path

from prism.context.project_scanner import scan_project
from prism.logging.logger import get_logger
from prism.rag.chunker import CodeDocumentChunker
from prism.rag.embeddings import BaseEmbeddingProvider, DeterministicEmbeddingProvider
from prism.rag.schemas import RAGQueryRequest, RAGSearchResult, RetrievedChunk
from prism.rag.vector_store import VectorStore

logger = get_logger(__name__)

SUPPORTED_EXTENSIONS = {
    ".py",
    ".md",
    ".txt",
    ".ts",
    ".js",
    ".json",
    ".yaml",
    ".yml",
    ".sql",
    ".rs",
    ".go",
}


class RAGService:
    """Service managing project indexing, semantic search, and context synthesis."""

    def __init__(
        self,
        vector_store: VectorStore | None = None,
        embedding_provider: BaseEmbeddingProvider | None = None,
        chunker: CodeDocumentChunker | None = None,
    ) -> None:
        self.vector_store = vector_store or VectorStore()
        self.embedding_provider = embedding_provider or DeterministicEmbeddingProvider()
        self.chunker = chunker or CodeDocumentChunker()

    async def index_file(self, file_path: str, content: str | None = None) -> int:
        """Chunk, embed, and store a single source or documentation file."""
        if content is None:
            path_obj = Path(file_path).expanduser().resolve()
            if not path_obj.exists() or not path_obj.is_file():
                raise FileNotFoundError(f"File not found for indexing: {file_path}")
            content = path_obj.read_text(encoding="utf-8", errors="replace")

        chunks = self.chunker.chunk_file(file_path, content)
        if not chunks:
            return 0

        # Generate embeddings in batch
        texts = [c.content for c in chunks]
        embeddings = await self.embedding_provider.embed_batch(texts)

        for chunk, emb in zip(chunks, embeddings, strict=True):
            chunk.embedding = emb

        # Remove existing chunks for this file to support clean document updates
        self.vector_store.delete_file(file_path)

        count = self.vector_store.add_chunks(chunks)
        logger.debug("Indexed file | path=%s | chunks=%d", file_path, count)
        return count

    def delete_file(self, file_path: str) -> int:
        """Remove a file and its chunks from the vector index."""
        return self.vector_store.delete_file(file_path)

    async def index_project(self, project_path: str, max_files: int = 100) -> int:
        """Scan project directory and index supported code and documentation files."""
        start_time = time.monotonic()
        root = Path(project_path).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            logger.warning(
                "RAG indexing rejected: invalid project path %s", project_path
            )
            return 0

        discovered_rel_paths = scan_project(root)
        total_chunks = 0
        indexed_files = 0

        for rel_path in discovered_rel_paths:
            if indexed_files >= max_files:
                break

            full_path = root / rel_path
            if full_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue

            try:
                content = full_path.read_text(encoding="utf-8", errors="replace")
                chunks_added = await self.index_file(str(full_path), content)
                total_chunks += chunks_added
                indexed_files += 1
            except (OSError, UnicodeDecodeError, ValueError, RuntimeError) as e:
                logger.warning(
                    "Could not read file for indexing: %s | error=%s", full_path, e
                )

        duration = round(time.monotonic() - start_time, 2)
        logger.info(
            "RAG project indexing complete | root=%s | files=%d | total_chunks=%d | duration=%.2fs",
            root,
            indexed_files,
            total_chunks,
            duration,
        )
        return total_chunks

    async def search(self, request: RAGQueryRequest) -> RAGSearchResult:
        """Perform semantic retrieval for a developer query with telemetry."""
        start_time = time.monotonic()
        query_embedding = await self.embedding_provider.embed_text(request.query)

        chunks = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=request.top_k,
            min_score=request.min_score,
            project_path=request.project_path,
            language=request.language,
        )
        duration_ms = round((time.monotonic() - start_time) * 1000.0, 2)

        logger.info(
            "RAG search executed | query='%s' | hits=%d | duration_ms=%.2fms",
            request.query[:50],
            len(chunks),
            duration_ms,
        )

        return RAGSearchResult(
            query=request.query,
            chunks=chunks,
            total_retrieved=len(chunks),
            duration_ms=duration_ms,
        )

    async def build_rag_context(
        self,
        query: str,
        project_path: str | None = None,
        top_k: int = 4,
    ) -> tuple[str, list[RetrievedChunk]]:
        """Retrieve relevant context and format as safe citation blocks."""
        search_res = await self.search(
            RAGQueryRequest(
                query=query,
                project_path=project_path,
                top_k=top_k,
                min_score=0.1,
            )
        )
        if not search_res.chunks:
            return "", []

        blocks: list[str] = []
        for rc in search_res.chunks:
            blocks.append(
                f"### {rc.citation} (Relevance Score: {rc.score})\n"
                f"```{rc.chunk.language or 'text'}\n"
                f"{rc.chunk.content}\n"
                f"```"
            )

        return "\n\n".join(blocks), search_res.chunks
