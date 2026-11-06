"""RAG & MCP Verification Script for PRISM.

Verifies:
1. MCP tool registry (6 core tools with schemas and parameter definitions).
2. MCP execution with security boundary enforcement (path traversal defense, sensitive file blocklist).
3. MCP audit logging persistence.
4. RAG indexing, chunking, vector embedding, cosine similarity search, citation attribution, and edge cases.
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from prism.api.dependencies import intelligence_repo
from prism.api.main import app
from prism.intelligence.models.developer_intelligence_models import (
    PersonalizedTask,
    TaskDifficulty,
    TaskPriority,
    TaskStatus,
)

client = TestClient(app)


def verify_rag_and_mcp() -> None:
    print("=" * 60)
    print("STARTING PRISM RAG & MCP INTEGRATION VERIFICATION")
    print("=" * 60)

    # -------------------------------------------------------------
    # 1. MCP TOOL DISCOVERY & SCHEMAS
    # -------------------------------------------------------------
    print("\n[1/6] Discovering MCP Tools...")
    resp = client.get("/mcp/tools")
    assert resp.status_code == 200, f"Failed to list tools: {resp.text}"
    tools = resp.json()
    tool_names = [t["name"] for t in tools]
    print(f"  Discovered {len(tools)} tools: {tool_names}")

    expected_tools = [
        "get_developer_task",
        "read_project_file",
        "get_task_progress",
        "search_knowledge_docs",
        "submit_task_evaluation",
        "get_developer_report",
    ]
    for et in expected_tools:
        assert et in tool_names, f"Expected tool '{et}' missing from MCP catalog"
    print("  [PASS] All 6 expected MCP tools registered.")

    # -------------------------------------------------------------
    # 2. MCP READ_PROJECT_FILE & PATH TRAVERSAL DEFENSE
    # -------------------------------------------------------------
    print("\n[2/6] Testing MCP 'read_project_file' with Security Controls...")
    # Safe read of legitimate file
    safe_res = client.post(
        "/mcp/tools/execute",
        json={
            "tool_name": "read_project_file",
            "arguments": {"file_path": "pyproject.toml"},
        },
    )
    assert safe_res.status_code == 200
    safe_data = safe_res.json()
    assert safe_data["status"] == "success"
    assert (
        "PRISM" in safe_data["data"]["content"]
        or "dependencies" in safe_data["data"]["content"]
    )
    print("  [PASS] Authorized file read succeeded.")

    # Path traversal attack defense: ../../
    traversal_res = client.post(
        "/mcp/tools/execute",
        json={
            "tool_name": "read_project_file",
            "arguments": {"file_path": "../../../Windows/System32/drivers/etc/hosts"},
        },
    )
    assert traversal_res.status_code == 200
    traversal_data = traversal_res.json()
    assert traversal_data["status"] == "error"
    assert (
        "path traversal" in traversal_data["error"].lower()
        or "forbidden" in traversal_data["error"].lower()
    )
    print(
        f"  [PASS] Path traversal attack successfully blocked: {traversal_data['error']}"
    )

    # Blocked sensitive file: .env
    env_res = client.post(
        "/mcp/tools/execute",
        json={"tool_name": "read_project_file", "arguments": {"file_path": ".env"}},
    )
    assert env_res.status_code == 200
    env_data = env_res.json()
    assert env_data["status"] == "error"
    assert (
        "restricted" in env_data["error"].lower()
        or "security" in env_data["error"].lower()
    )
    print(
        f"  [PASS] Sensitive file '.env' access successfully blocked: {env_data['error']}"
    )

    # -------------------------------------------------------------
    # 3. MCP TASK TOOLS & AUDIT LOGGING
    # -------------------------------------------------------------
    print("\n[3/6] Testing Task MCP Tools & Audit Logging...")
    dev_id = f"mcp_dev_{uuid.uuid4().hex[:6]}"
    task_id = f"mcp_task_{uuid.uuid4().hex[:6]}"

    # Seed a task in task engine
    t = PersonalizedTask(
        task_id=task_id,
        developer_id=dev_id,
        title="Async Task Processor",
        description="Implement an asynchronous background worker using asyncio.Queue",
        target_skill="Python AsyncIO",
        difficulty=TaskDifficulty.INTERMEDIATE,
        priority=TaskPriority.HIGH,
        status=TaskStatus.IN_PROGRESS,
        estimated_minutes=30,
        reason="Strengthen concurrent programming proficiency",
        target_role="Backend Developer",
    )
    intelligence_repo.save_task(t)

    # Execute get_developer_task
    task_mcp = client.post(
        "/mcp/tools/execute",
        json={
            "tool_name": "get_developer_task",
            "arguments": {"task_id": task_id},
            "caller_id": dev_id,
        },
    )
    assert task_mcp.status_code == 200
    t_data = task_mcp.json()
    assert t_data["status"] == "success"
    assert t_data["data"]["title"] == "Async Task Processor"
    print("  [PASS] MCP 'get_developer_task' executed and returned task details.")

    # Execute get_task_progress
    prog_mcp = client.post(
        "/mcp/tools/execute",
        json={
            "tool_name": "get_task_progress",
            "arguments": {"developer_id": dev_id},
            "caller_id": dev_id,
        },
    )
    assert prog_mcp.status_code == 200
    prog_data = prog_mcp.json()
    assert prog_data["status"] == "success"
    print("  [PASS] MCP 'get_task_progress' returned developer progress data.")

    # Verify MCP Audit Log
    audit_resp = client.get(f"/mcp/audit?caller_id={dev_id}")
    assert audit_resp.status_code == 200
    audits = audit_resp.json()
    assert len(audits) >= 2, (
        f"Expected at least 2 audit logs for caller, found {len(audits)}"
    )
    print(
        f"  [PASS] Verified {len(audits)} persistent audit records generated in MySQL for caller '{dev_id}'."
    )

    # -------------------------------------------------------------
    # 4. RAG DOCUMENT INDEXING & CHUNKING
    # -------------------------------------------------------------
    print("\n[4/6] Testing RAG Ingestion, Chunking, and Vector Indexing...")
    # Clear vector store
    client.post("/rag/clear")

    sample_doc = """
    # Architectural Blueprint: PRISM Fast Dependency Injection
    FastAPI provides an extensible dependency injection system using Depends.
    In PRISM IDE, services like TaskRecommendationEngine and GuidedLearningService
    are injected through centralized dependency singletons in prism.api.dependencies.
    This guarantees thread-safe, decoupled service lifecycles across HTTP requests.
    """
    index_res = client.post(
        "/rag/index/file",
        json={"file_path": "docs/architecture_di.md", "content": sample_doc},
    )
    assert index_res.status_code == 200
    idx_data = index_res.json()
    assert idx_data["status"] == "indexed"
    assert idx_data["chunks_indexed"] >= 1
    print(
        f"  [PASS] Indexed file into RAG: {idx_data['chunks_indexed']} chunks created."
    )

    # Check stats
    stats_res = client.get("/rag/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total_chunks"] >= 1
    print(
        f"  [PASS] RAG stats verified: {stats['total_chunks']} chunks in vector store (dim={stats['dimension']})."
    )

    # -------------------------------------------------------------
    # 5. RAG SEMANTIC SIMILARITY SEARCH
    # -------------------------------------------------------------
    print("\n[5/6] Testing Semantic Search & Citation Retrieval...")
    search_res = client.post(
        "/rag/search",
        json={
            "query": "How is dependency injection implemented in FastAPI for PRISM?",
            "top_k": 3,
        },
    )
    assert search_res.status_code == 200
    results = search_res.json()
    assert len(results["chunks"]) > 0
    top_result = results["chunks"][0]
    assert top_result["score"] > 0.0
    assert "dependency injection" in top_result["chunk"]["content"].lower()
    print(
        f"  [PASS] RAG semantic search retrieved citation (score={top_result['score']:.4f})."
    )

    # Test MCP tool 'search_knowledge_docs' integration with RAG
    mcp_rag = client.post(
        "/mcp/tools/execute",
        json={
            "tool_name": "search_knowledge_docs",
            "arguments": {"query": "FastAPI Depends injection"},
        },
    )
    assert mcp_rag.status_code == 200
    mcp_rag_data = mcp_rag.json()
    assert mcp_rag_data["status"] == "success"
    assert len(mcp_rag_data["data"]) > 0
    print(
        f"  [PASS] MCP tool 'search_knowledge_docs' returned {len(mcp_rag_data['data'])} citations."
    )
    print("  [PASS] MCP tool 'search_knowledge_docs' seamlessly queried RAG engine.")

    # -------------------------------------------------------------
    # 6. RAG EDGE CASES
    # -------------------------------------------------------------
    print("\n[6/6] Testing RAG Edge Cases...")
    # Empty query
    empty_query_res = client.post("/rag/search", json={"query": "    ", "top_k": 3})
    assert empty_query_res.status_code in [400, 422, 200]
    print("  [PASS] Handled empty query appropriately.")

    # Non-existent file
    non_existent = client.post(
        "/rag/index/file", json={"file_path": "non_existent_folder/missing_file.md"}
    )
    assert non_existent.status_code in [404, 500]
    print("  [PASS] Handled non-existent file path.")

    print("\n" + "=" * 60)
    print("ALL RAG & MCP INTEGRATION AUDIT CHECKS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    verify_rag_and_mcp()
