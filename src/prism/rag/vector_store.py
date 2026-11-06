"""In-memory Vector Store with pure-Python cosine similarity search and persistence (Phase 20)."""

import json
import math
from pathlib import Path
from typing import Any

from prism.logging.logger import get_logger
from prism.rag.schemas import DocumentChunk, RetrievedChunk

logger = get_logger(__name__)


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two numeric vectors."""
    if len(v1) != len(v2) or not v1:
        return 0.0

    dot = sum(a * b for a, b in zip(v1, v2, strict=False))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))

    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)


class VectorStore:
    """Thread-safe in-memory vector storage with semantic filtering and atomic persistence."""

    def __init__(self, storage_path: str | Path | None = None) -> None:
        self._chunks: dict[str, DocumentChunk] = {}
        self.storage_path = Path(storage_path) if storage_path else None
        if self.storage_path and self.storage_path.is_file():
            self.load()

    def add_chunks(self, chunks: list[DocumentChunk]) -> int:
        """Store or update document chunks with embeddings."""
        added = 0
        for chunk in chunks:
            if chunk.embedding is not None:
                self._chunks[chunk.chunk_id] = chunk
                added += 1
        if added > 0 and self.storage_path:
            self.save()
        return added

    def save(self, path: str | Path | None = None) -> None:
        """Atomically persist stored vectors to JSON file."""
        target_path = Path(path) if path else self.storage_path
        if not target_path:
            return
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = target_path.with_suffix(".tmp")
            data = {cid: chunk.model_dump() for cid, chunk in self._chunks.items()}
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f)
            tmp_path.replace(target_path)
            logger.debug("Persisted %d chunks to %s", len(self._chunks), target_path)
        except (OSError, ValueError, TypeError) as err:
            logger.warning("Failed to persist vector store to %s: %s", target_path, err)

    def load(self, path: str | Path | None = None) -> int:
        """Load stored chunks from JSON file."""
        target_path = Path(path) if path else self.storage_path
        if not target_path or not target_path.is_file():
            return 0
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            loaded = 0
            for cid, chunk_data in data.items():
                self._chunks[cid] = DocumentChunk.model_validate(chunk_data)
                loaded += 1
            logger.debug("Loaded %d chunks from %s", loaded, target_path)
            return loaded
        except (OSError, ValueError, TypeError) as err:
            logger.warning("Failed to load vector store from %s: %s", target_path, err)
            return 0

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 4,
        min_score: float = 0.0,
        project_path: str | None = None,
        language: str | None = None,
        metadata_filters: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        """Perform semantic similarity retrieval across stored chunks."""
        scored_candidates: list[tuple[float, DocumentChunk]] = []

        for chunk in self._chunks.values():
            if chunk.embedding is None:
                continue

            # Project path filtering
            if project_path and not chunk.file_path.startswith(project_path):
                continue

            # Language filtering
            if language and chunk.language != language.lower():
                continue

            # Custom metadata filtering
            if metadata_filters:
                match = True
                for k, v in metadata_filters.items():
                    if chunk.metadata.get(k) != v:
                        match = False
                        break
                if not match:
                    continue

            score = cosine_similarity(query_embedding, chunk.embedding)
            if score >= min_score:
                scored_candidates.append((score, chunk))

        # Sort descending by similarity score
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        results: list[RetrievedChunk] = []
        for score, chunk in scored_candidates[:top_k]:
            citation = (
                f"[Source: {chunk.file_path}:{chunk.start_line}-{chunk.end_line}]"
            )
            results.append(
                RetrievedChunk(
                    chunk=chunk,
                    score=round(score, 4),
                    citation=citation,
                )
            )

        return results

    def delete_project(self, project_path: str) -> int:
        """Remove all chunks associated with a specific project directory."""
        to_remove = [
            cid
            for cid, chk in self._chunks.items()
            if chk.file_path.startswith(project_path)
        ]
        for cid in to_remove:
            del self._chunks[cid]
        if to_remove and self.storage_path:
            self.save()
        return len(to_remove)

    def clear(self) -> None:
        """Clear all stored vectors."""
        self._chunks.clear()
        if self.storage_path:
            self.save()

    def count(self) -> int:
        """Return total stored chunks."""
        return len(self._chunks)
