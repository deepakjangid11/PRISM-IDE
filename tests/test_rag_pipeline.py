"""Unit tests for Phase 20 Pure-Python RAG Pipeline (AST chunking, embeddings, vector store)."""

from __future__ import annotations

from pathlib import Path

import pytest

from prism.rag.chunker import CodeDocumentChunker
from prism.rag.embeddings import DeterministicEmbeddingProvider, RemoteEmbeddingProvider
from prism.rag.schemas import DocumentChunk, RAGQueryRequest
from prism.rag.service import RAGService
from prism.rag.vector_store import VectorStore


def test_chunker_python_ast() -> None:
    code = (
        '"""Module docstring for testing."""\n'
        "\n"
        "def sync_function(a: int) -> int:\n"
        "    return a + 1\n"
        "\n"
        "async def async_handler():\n"
        "    return 'ok'\n"
        "\n"
        "class Calculator:\n"
        "    def add(self, x, y):\n"
        "        return x + y\n"
    )

    chunker = CodeDocumentChunker()
    chunks = chunker.chunk_file(file_path="src/calc.py", content=code)

    assert len(chunks) >= 3
    # Verify module docstring or functions
    func_chunks = [c for c in chunks if c.metadata.get("kind") == "function"]
    class_chunks = [c for c in chunks if c.metadata.get("kind") == "class"]

    assert len(func_chunks) == 2
    assert len(class_chunks) == 1
    assert any("sync_function" in c.content for c in func_chunks)
    assert any("async_handler" in c.content for c in func_chunks)
    assert "class Calculator" in class_chunks[0].content
    assert class_chunks[0].language == "python"


def test_chunker_fallback_sliding_window() -> None:
    markdown = "\n\n".join(
        [f"Paragraph {i}: Documentation content about topic." for i in range(10)]
    )
    chunker = CodeDocumentChunker(default_chunk_size=30, default_chunk_overlap=10)
    chunks = chunker.chunk_file(file_path="docs/guide.md", content=markdown)

    assert len(chunks) > 1
    assert all(c.chunk_type == "markdown" for c in chunks)
    assert chunks[0].language == "md"
    assert chunks[0].start_line == 1


def test_chunker_empty_content() -> None:
    chunker = CodeDocumentChunker()
    chunks = chunker.chunk_file(file_path="empty.py", content="   \n  \n")
    assert chunks == []


def test_chunker_syntax_error_fallback() -> None:
    chunker = CodeDocumentChunker()
    broken_code = "def invalid syntax ((\n    print('test')\n"
    chunks = chunker.chunk_file(file_path="broken.py", content=broken_code)
    assert len(chunks) > 0
    assert chunks[0].language == "python"

    # Non-python non-markdown file (e.g. javascript)
    js_code = "function add(a, b) {\n    return a + b;\n}\n"
    js_chunks = chunker.chunk_file(file_path="script.js", content=js_code)
    assert len(js_chunks) > 0
    assert js_chunks[0].chunk_type == "code"


@pytest.mark.anyio
async def test_deterministic_embedding_provider() -> None:
    provider = DeterministicEmbeddingProvider(dimension=128)
    assert provider.dimension == 128

    vec1 = await provider.embed_text("FastAPI route endpoint and dependency injection")
    vec2 = await provider.embed_text("FastAPI API endpoints and routing dependencies")
    vec3 = await provider.embed_text("Baking chocolate chip cookies and banana bread")

    assert len(vec1) == 128
    # Norm check (approx 1.0)
    norm1 = sum(x * x for x in vec1) ** 0.5
    assert abs(norm1 - 1.0) < 0.05

    # Semantic similarity: related queries should have higher dot product
    dot_related = sum(a * b for a, b in zip(vec1, vec2, strict=True))
    dot_unrelated = sum(a * b for a, b in zip(vec1, vec3, strict=True))

    assert dot_related > dot_unrelated


@pytest.mark.anyio
async def test_deterministic_embedding_batch() -> None:
    provider = DeterministicEmbeddingProvider(dimension=64)
    texts = ["one", "two", "three"]
    vectors = await provider.embed_batch(texts)
    assert len(vectors) == 3
    assert all(len(v) == 64 for v in vectors)


@pytest.mark.anyio
async def test_remote_embedding_provider_fallback() -> None:
    # Remote provider configured with invalid URL will fallback to deterministic
    provider = RemoteEmbeddingProvider(
        api_key="test", base_url="http://invalid-endpoint-domain/embed", dimension=128
    )
    vec = await provider.embed_text("Fallback test query")
    assert len(vec) == 128
    assert isinstance(vec[0], float)


def test_vector_store_operations() -> None:
    store = VectorStore()
    chunk1 = DocumentChunk(
        chunk_id="c1",
        file_path="src/api.py",
        content="async def get_users(): return []",
        start_line=1,
        end_line=2,
        language="python",
        embedding=[0.8, 0.6],
    )
    chunk2 = DocumentChunk(
        chunk_id="c2",
        file_path="src/math.py",
        content="def add(a, b): return a + b",
        start_line=10,
        end_line=11,
        language="python",
        embedding=[0.0, 1.0],
    )

    store.add_chunks([chunk1, chunk2])
    assert store.count() == 2

    # Query vector close to chunk1: [1.0, 0.0]
    hits = store.search(query_embedding=[1.0, 0.0], top_k=2)
    assert len(hits) == 2
    assert hits[0].chunk.chunk_id == "c1"
    assert hits[0].citation == "[Source: src/api.py:1-2]"

    # Search with min_score filter
    filtered = store.search(query_embedding=[1.0, 0.0], top_k=2, min_score=0.5)
    assert len(filtered) == 1
    assert filtered[0].chunk.chunk_id == "c1"

    # Search with language filter
    non_matches = store.search(query_embedding=[1.0, 0.0], language="rust")
    assert len(non_matches) == 0

    # Search with project_path filter
    proj_matches = store.search(
        query_embedding=[1.0, 0.0], project_path="nonexistent_proj"
    )
    assert len(proj_matches) == 0

    # Search with metadata filter
    meta_matches = store.search(
        query_embedding=[1.0, 0.0],
        metadata_filters={"custom_key": "custom_val"},
    )
    assert len(meta_matches) == 0

    # Test delete_project
    del_count = store.delete_project("src/api")
    assert del_count == 1
    assert store.count() == 1

    store.clear()
    assert store.count() == 0


@pytest.mark.anyio
async def test_rag_service_index_and_retrieve(tmp_path: Path) -> None:
    service = RAGService(
        embedding_provider=DeterministicEmbeddingProvider(dimension=64)
    )

    test_file = tmp_path / "service.py"
    test_file.write_text(
        "class AuthService:\n"
        "    def authenticate(self, token: str) -> bool:\n"
        "        return token == 'valid_token'\n",
        encoding="utf-8",
    )

    chunks_count = await service.index_file(str(test_file))
    assert chunks_count > 0
    assert service.vector_store.count() >= chunks_count

    req = RAGQueryRequest(query="How does authentication work?", top_k=3)
    res = await service.search(req)

    assert res.total_retrieved > 0
    assert "AuthService" in res.chunks[0].chunk.content
    assert res.duration_ms >= 0.0

    # Build RAG context block
    context_text, retrieved_chunks = await service.build_rag_context(
        query="How does authentication work?", top_k=2
    )
    assert len(retrieved_chunks) > 0
    assert "AuthService" in context_text
    assert "Relevance Score" in context_text


@pytest.mark.anyio
async def test_rag_service_index_project(tmp_path: Path) -> None:
    service = RAGService()

    # Create small project directory
    (tmp_path / "models.py").write_text("class User: name: str\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "# Project PRISM\nLearning assistant\n", encoding="utf-8"
    )

    total_indexed = await service.index_project(str(tmp_path))
    assert total_indexed >= 2


def test_vector_store_persistence(tmp_path: Path) -> None:
    store_file = tmp_path / "rag_store.json"
    store1 = VectorStore(storage_path=store_file)
    c1 = DocumentChunk(
        chunk_id="c1",
        file_path="src/main.py",
        content="def start(): pass",
        embedding=[0.5, 0.5],
    )
    c2 = DocumentChunk(
        chunk_id="c2",
        file_path="src/helper.py",
        content="def help(): pass",
        embedding=[0.1, 0.9],
    )
    store1.add_chunks([c1, c2])
    assert store1.count() == 2
    assert store_file.is_file()

    # Re-instantiate new VectorStore pointing to same path
    store2 = VectorStore(storage_path=store_file)
    assert store2.count() == 2
    res = store2.search([0.5, 0.5], top_k=1)
    assert len(res) == 1
    assert res[0].chunk.chunk_id == "c1"

    # Test delete updates persistence
    store2.delete_project("src/main")
    assert store2.count() == 1

    store3 = VectorStore(storage_path=store_file)
    assert store3.count() == 1
    assert "c2" in store3._chunks


def test_vector_store_edge_cases() -> None:
    from prism.rag.vector_store import cosine_similarity

    assert cosine_similarity([], []) == 0.0
    assert cosine_similarity([1.0], [1.0, 2.0]) == 0.0
    assert cosine_similarity([0.0, 0.0], [0.0, 0.0]) == 0.0

    store = VectorStore()
    chunk = DocumentChunk(
        chunk_id="chunk_edge",
        file_path="src/main.py",
        content="code",
        metadata={"env": "prod", "tag": "v1"},
        embedding=[1.0, 0.0],
    )
    store.add_chunks([chunk])

    # Search with min_score threshold not met
    assert len(store.search([0.0, 1.0], min_score=0.5)) == 0

    # Search with non-matching metadata filter
    assert len(store.search([1.0, 0.0], metadata_filters={"env": "dev"})) == 0
    assert len(store.search([1.0, 0.0], metadata_filters={"env": "prod"})) == 1


@pytest.mark.anyio
async def test_remote_embedding_provider_empty_key_fallback() -> None:
    from prism.rag.embeddings import RemoteEmbeddingProvider

    provider = RemoteEmbeddingProvider(api_key="")
    assert provider.dimension == 1536
    vec = await provider.embed_text("test")
    assert len(vec) == 1536
    batch = await provider.embed_batch(["test1", "test2"])
    assert len(batch) == 2


@pytest.mark.anyio
async def test_rag_service_edge_cases(tmp_path: Path) -> None:
    service = RAGService()

    # 1. index_file without content for non-existent file -> raises FileNotFoundError
    with pytest.raises(FileNotFoundError, match="File not found for indexing"):
        await service.index_file(str(tmp_path / "non_existent.py"))

    # 2. index_file with empty content -> returns 0
    assert await service.index_file(str(tmp_path / "empty.py"), content="   \n") == 0

    # 3. index_project on non-existent directory -> returns 0
    assert await service.index_project(str(tmp_path / "does_not_exist")) == 0

    # 4. index_project with max_files and unsupported extensions
    sub_dir = tmp_path / "rag_edge_proj"
    sub_dir.mkdir()
    (sub_dir / "file1.py").write_text("def a(): pass\n", encoding="utf-8")
    (sub_dir / "file2.py").write_text("def b(): pass\n", encoding="utf-8")
    (sub_dir / "binary.png").write_text("fake binary", encoding="utf-8")

    # max_files=1 should index only 1 file
    indexed_1 = await service.index_project(str(sub_dir), max_files=1)
    assert indexed_1 >= 1

    # 5. build_rag_context when search produces no hits
    empty_service = RAGService()
    ctx_text, hits = await empty_service.build_rag_context("any query")
    assert ctx_text == ""
    assert hits == []


@pytest.mark.anyio
async def test_rag_service_index_project_read_error(tmp_path: Path) -> None:
    from unittest.mock import patch

    service = RAGService()
    proj_dir = tmp_path / "read_err_proj"
    proj_dir.mkdir()
    test_file = proj_dir / "err.py"
    test_file.write_text("def ok(): pass\n", encoding="utf-8")

    # Simulate OSError when reading the file
    with patch.object(Path, "read_text", side_effect=OSError("Read failure")):
        count = await service.index_project(str(proj_dir))
        assert count == 0
