"""PRISM Backend Performance Benchmarking Script.

Measures:
1. API Route Latencies (P50, P95, Min, Max, Avg) across core operational endpoints.
2. MySQL Database Query Latencies.
3. RAG Semantic Search Latency.
4. Personalized Task Generation Latency.
5. Static AST Code Evaluation Latency.

Outputs structured JSON telemetry to docs/performance_benchmarks.json.
"""

from __future__ import annotations

import json
import statistics
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import text

from prism.api.main import app
from prism.storage.database import session_scope

client = TestClient(app)


def _percentile(data: list[float], p: float) -> float:
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = int(len(sorted_data) * (p / 100.0))
    idx = min(idx, len(sorted_data) - 1)
    return round(sorted_data[idx], 2)


def benchmark() -> dict[str, Any]:
    print("=" * 65)
    print("STARTING PRISM BACKEND PERFORMANCE BENCHMARKING SUITE")
    print("=" * 65)

    # 1. Setup Developer & Authentication
    uid = uuid.uuid4().hex[:8]
    dev_id = f"bench_{uid}"
    email = f"bench_{uid}@prism.io"
    password = "BenchmarkPassword2026!"

    reg = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
            "name": f"Benchmark User {uid}",
            "developer_id": dev_id,
            "role": "developer",
        },
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    metrics: dict[str, Any] = {}

    # -----------------------------------------------------------------
    # Benchmark 1: API Route Latency across Core Groups
    # -----------------------------------------------------------------
    print("\n[1/5] Benchmarking API Route Response Latencies...")
    endpoints = [
        ("GET /health", lambda: client.get("/health")),
        ("GET /auth/me", lambda: client.get("/auth/me", headers=headers)),
        (
            "GET /skills/profile/{id}",
            lambda: client.get(f"/skills/profile/{dev_id}", headers=headers),
        ),
        (
            "GET /progress/{id}/dashboard",
            lambda: client.get(f"/progress/{dev_id}/dashboard", headers=headers),
        ),
        ("GET /mcp/tools", lambda: client.get("/mcp/tools")),
        ("GET /rag/stats", lambda: client.get("/rag/stats")),
    ]

    api_results: dict[str, dict[str, float]] = {}
    N_RUNS = 20

    for name, call_fn in endpoints:
        latencies: list[float] = []
        for _ in range(N_RUNS):
            t0 = time.perf_counter()
            resp = call_fn()
            duration_ms = (time.perf_counter() - t0) * 1000.0
            assert resp.status_code == 200, f"{name} failed with {resp.status_code}"
            latencies.append(duration_ms)

        api_results[name] = {
            "p50_ms": _percentile(latencies, 50),
            "p95_ms": _percentile(latencies, 95),
            "avg_ms": round(statistics.mean(latencies), 2),
            "min_ms": round(min(latencies), 2),
            "max_ms": round(max(latencies), 2),
        }
        print(
            f"  {name:30s} -> P50: {api_results[name]['p50_ms']}ms | P95: {api_results[name]['p95_ms']}ms | Avg: {api_results[name]['avg_ms']}ms"
        )

    metrics["api_endpoints"] = api_results

    # -----------------------------------------------------------------
    # Benchmark 2: MySQL Query Latencies
    # -----------------------------------------------------------------
    print("\n[2/5] Benchmarking MySQL Database Query Latencies...")
    db_latencies: list[float] = []
    for _ in range(30):
        t0 = time.perf_counter()
        with session_scope() as session:
            session.execute(
                text(
                    "SELECT developer_id, email FROM developers WHERE developer_id = :id"
                ),
                {"id": dev_id},
            ).fetchone()
        db_latencies.append((time.perf_counter() - t0) * 1000.0)

    metrics["database_query"] = {
        "p50_ms": _percentile(db_latencies, 50),
        "p95_ms": _percentile(db_latencies, 95),
        "avg_ms": round(statistics.mean(db_latencies), 2),
        "min_ms": round(min(db_latencies), 2),
        "max_ms": round(max(db_latencies), 2),
    }
    print(
        f"  MySQL Point Lookup -> P50: {metrics['database_query']['p50_ms']}ms | P95: {metrics['database_query']['p95_ms']}ms | Avg: {metrics['database_query']['avg_ms']}ms"
    )

    # -----------------------------------------------------------------
    # Benchmark 3: RAG Retrieval Latency
    # -----------------------------------------------------------------
    print("\n[3/5] Benchmarking RAG Semantic Retrieval Latency...")
    # Pre-index a chunk
    client.post(
        "/rag/index/file",
        json={
            "file_path": "bench.py",
            "content": "def fibonacci(n): return n if n < 2 else fibonacci(n-1) + fibonacci(n-2)",
        },
    )
    rag_latencies: list[float] = []
    for _ in range(15):
        t0 = time.perf_counter()
        resp = client.post(
            "/rag/search",
            json={"query": "fibonacci sequence calculation in python", "top_k": 3},
        )
        rag_latencies.append((time.perf_counter() - t0) * 1000.0)
        assert resp.status_code == 200

    metrics["rag_retrieval"] = {
        "p50_ms": _percentile(rag_latencies, 50),
        "p95_ms": _percentile(rag_latencies, 95),
        "avg_ms": round(statistics.mean(rag_latencies), 2),
        "min_ms": round(min(rag_latencies), 2),
        "max_ms": round(max(rag_latencies), 2),
    }
    print(
        f"  RAG Semantic Search -> P50: {metrics['rag_retrieval']['p50_ms']}ms | P95: {metrics['rag_retrieval']['p95_ms']}ms | Avg: {metrics['rag_retrieval']['avg_ms']}ms"
    )

    # -----------------------------------------------------------------
    # Benchmark 4: Task Recommendation Generation Latency
    # -----------------------------------------------------------------
    print("\n[4/5] Benchmarking Task Recommendation Engine Latency...")
    task_latencies: list[float] = []
    for _ in range(10):
        t0 = time.perf_counter()
        resp = client.post(
            "/tasks/generate",
            json={
                "developer_id": dev_id,
                "target_role": "Backend Developer",
                "target_goal": "Python",
                "limit": 2,
            },
            headers=headers,
        )
        task_latencies.append((time.perf_counter() - t0) * 1000.0)
        assert resp.status_code == 200

    metrics["task_generation"] = {
        "p50_ms": _percentile(task_latencies, 50),
        "p95_ms": _percentile(task_latencies, 95),
        "avg_ms": round(statistics.mean(task_latencies), 2),
        "min_ms": round(min(task_latencies), 2),
        "max_ms": round(max(task_latencies), 2),
    }
    print(
        f"  Task Generation Engine -> P50: {metrics['task_generation']['p50_ms']}ms | P95: {metrics['task_generation']['p95_ms']}ms | Avg: {metrics['task_generation']['avg_ms']}ms"
    )

    # -----------------------------------------------------------------
    # Benchmark 5: Static AST Code Evaluation Latency
    # -----------------------------------------------------------------
    print("\n[5/5] Benchmarking Static AST Code Evaluation Engine Latency...")
    from prism.api.dependencies import intelligence_repo
    from prism.intelligence.models.developer_intelligence_models import (
        PersonalizedTask,
        TaskDifficulty,
        TaskPriority,
        TaskStatus,
    )

    task_id = f"bench_task_{uid}"
    t = PersonalizedTask(
        task_id=task_id,
        developer_id=dev_id,
        title="Benchmark Solve Task",
        description="Write a solve function",
        target_skill="Python",
        difficulty=TaskDifficulty.INTERMEDIATE,
        priority=TaskPriority.HIGH,
        status=TaskStatus.IN_PROGRESS,
        estimated_minutes=30,
        reason="Benchmark evaluation",
        target_role="Backend Developer",
    )
    intelligence_repo.save_task(t)

    eval_latencies: list[float] = []
    for _ in range(10):
        # Create submission
        sub_resp = client.post(
            f"/tasks/{task_id}/submit",
            json={
                "developer_id": dev_id,
                "submission_type": "code",
                "source_code": "def solve(x): return x * 2",
            },
            headers=headers,
        )
        sub_id = sub_resp.json()["submission_id"]

        t0 = time.perf_counter()
        ev_resp = client.post(f"/evaluation/submissions/{sub_id}", headers=headers)
        eval_latencies.append((time.perf_counter() - t0) * 1000.0)
        assert ev_resp.status_code == 200

    metrics["ast_evaluation"] = {
        "p50_ms": _percentile(eval_latencies, 50),
        "p95_ms": _percentile(eval_latencies, 95),
        "avg_ms": round(statistics.mean(eval_latencies), 2),
        "min_ms": round(min(eval_latencies), 2),
        "max_ms": round(max(eval_latencies), 2),
    }
    print(
        f"  AST Code Evaluation -> P50: {metrics['ast_evaluation']['p50_ms']}ms | P95: {metrics['ast_evaluation']['p95_ms']}ms | Avg: {metrics['ast_evaluation']['avg_ms']}ms"
    )

    # Output to docs/performance_benchmarks.json
    out_path = Path("docs/performance_benchmarks.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print("\n" + "=" * 65)
    print(f"BENCHMARKS COMPLETED. SAVED TO {out_path.resolve()}")
    print("=" * 65)
    return metrics


if __name__ == "__main__":
    benchmark()
