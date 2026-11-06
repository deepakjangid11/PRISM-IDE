import uuid

import pytest
from fastapi.testclient import TestClient

from prism.api.dependencies import (
    developer_repo,
    evaluation_engine,
    guided_learning_service,
    intelligence_repo,
    mcp_service,
    report_generator,
    task_engine,
    task_platform_repo,
)
from prism.api.main import app
from prism.intelligence.models.developer_intelligence_models import (
    PersonalizedTask,
    TaskDifficulty,
    TaskPriority,
    TaskStatus,
)
from prism.intelligence.models.task_platform_models import (
    GuidanceLevel,
)

client = TestClient(app)


def test_task_recommendation_specifications() -> None:
    spec_beginner = task_engine._build_task_specification(
        skill_name="Python AsyncIO",
        diff=TaskDifficulty.BEGINNER,
        target_role="Backend Developer",
        prereqs=["Python Basics"],
        importance_reason="AsyncIO is essential for scalable backends",
    )
    assert "Foundational" in spec_beginner["title"]
    assert len(spec_beginner["learning_objectives"]) >= 2
    assert len(spec_beginner["requirements"]) >= 2
    assert len(spec_beginner["test_cases"]) >= 2
    assert len(spec_beginner["hints"]) >= 2

    spec_expert = task_engine._build_task_specification(
        skill_name="Distributed Transactions",
        diff=TaskDifficulty.EXPERT,
        target_role="Principal Architect",
        prereqs=["Database Fundamentals", "Distributed Systems"],
        importance_reason="High throughput consistency",
    )
    assert (
        "Architecture" in spec_expert["title"] or "Distributed" in spec_expert["title"]
    )
    assert len(spec_expert["hints"]) >= 3


def test_task_evaluation_engine_valid_and_invalid_code() -> None:
    dev_id = f"eval_dev_{uuid.uuid4().hex[:6]}"
    task_id = f"eval_task_{uuid.uuid4().hex[:6]}"

    # Setup task in repo
    task = PersonalizedTask(
        task_id=task_id,
        developer_id=dev_id,
        target_skill="python_concurrency",
        reason="Scalable backend development",
        title="Async Task Processor",
        description="Implement an asynchronous worker pool with retry handling",
        problem_statement="Build an async processor handling items reliably.",
        difficulty=TaskDifficulty.INTERMEDIATE,
        priority=TaskPriority.HIGH,
        estimated_minutes=180,
        status=TaskStatus.IN_PROGRESS,
        requirements=[
            "Use async def",
            "Handle errors with try/except",
            "Process items",
        ],
        acceptance_criteria=["Function worker exists", "Handles ValueError"],
    )
    intelligence_repo.save_task(task)

    # 1. Evaluate valid implementation
    valid_code = (
        "import asyncio\n"
        "class AsyncWorkerPool:\n"
        "    def __init__(self, max_concurrency: int = 5):\n"
        "        self.semaphore = asyncio.Semaphore(max_concurrency)\n\n"
        "    async def worker(self, item: dict) -> dict:\n"
        "        try:\n"
        "            if not item:\n"
        "                raise ValueError('Invalid item')\n"
        "            return {'status': 'processed', 'data': item}\n"
        "        except Exception as err:\n"
        "            return {'status': 'failed', 'error': str(err)}\n"
    )
    valid_sub = evaluation_engine.submit_work(
        task_id=task_id,
        developer_id=dev_id,
        submission_type="code",
        source_code=valid_code,
        explanation="First attempt with proper error handling and async class.",
    )

    eval_result = evaluation_engine.evaluate_submission(valid_sub.submission_id)
    assert eval_result.passed is True
    assert eval_result.score >= 70.0
    assert len(eval_result.strengths) >= 1
    assert (
        eval_result.generated_evidence_id is not None
    )  # Evidence generated upon passing
    assert len(eval_result.test_results) >= 2

    # Verify honest test results status
    for tc in eval_result.test_results:
        assert tc.execution_time_ms >= 0.0

    # 2. Evaluate invalid code with syntax error
    broken_code = "def broken_func(\n    missing closing paren and invalid syntax"
    broken_sub = evaluation_engine.submit_work(
        task_id=task_id,
        developer_id=dev_id,
        submission_type="code",
        source_code=broken_code,
    )
    broken_eval = evaluation_engine.evaluate_submission(broken_sub.submission_id)
    assert broken_eval.passed is False
    assert broken_eval.score < 50.0
    assert any("SyntaxError" in m for m in broken_eval.mistakes)
    assert broken_eval.generated_evidence_id is None


def test_guided_learning_service_and_anti_spoiler() -> None:
    dev_id = f"guide_dev_{uuid.uuid4().hex[:6]}"
    task_id = f"guide_task_{uuid.uuid4().hex[:6]}"

    task = PersonalizedTask(
        task_id=task_id,
        developer_id=dev_id,
        target_skill="database_optimization",
        reason="Performance and scale requirements",
        title="Index Optimization Challenge",
        description="Design compound indexes for low-latency range queries",
        problem_statement="Given slow range queries on order dates, design optimal indexing.",
        difficulty=TaskDifficulty.INTERMEDIATE,
        priority=TaskPriority.HIGH,
        estimated_minutes=120,
        status=TaskStatus.IN_PROGRESS,
        requirements=["Create multi-column index", "Ensure covering index"],
        hints=[
            "Review query filtering order",
            "Consider equality before range predicates",
            "Include projected columns in covering index",
        ],
    )
    intelligence_repo.save_task(task)

    # 1. Start conversation
    conv, first_msg = guided_learning_service.start_conversation(
        developer_id=dev_id,
        task_id=task_id,
        initial_query="How do I get started optimizing indexes?",
    )
    assert conv.developer_id == dev_id
    assert conv.task_id == task_id
    assert first_msg is not None

    # 2. Step-by-step guidance breakdown (Level 4)
    step_msg = guided_learning_service.send_message(
        conversation_id=conv.conversation_id,
        developer_message="Can you break this down for me?",
        requested_level=GuidanceLevel.STEP_BY_STEP,
        allow_solution=False,
    )
    assert "step-by-step" in step_msg.content.lower()

    # 3. Request progressive hints (Level 3)
    hint1 = guided_learning_service.request_hint(conv.conversation_id)
    assert "hint" in hint1.content.lower()

    hint2 = guided_learning_service.request_hint(conv.conversation_id)
    assert "hint" in hint2.content.lower()

    # 4. Debugging assistance without solution (Level 6, allow_solution=False)
    debug_msg = guided_learning_service.request_debug_assistance(
        conversation_id=conv.conversation_id,
        error_output="IndexError: tuple index out of range at line 14",
        code_snippet="row = cursor.fetchone()\nprint(row[5])",
    )
    assert "debugging" in debug_msg.content.lower()
    assert "Complete Solution Reference" not in debug_msg.content

    # 5. Explicit reference solution allowed only when requested (allow_solution=True)
    solution_msg = guided_learning_service.send_message(
        conversation_id=conv.conversation_id,
        developer_message="Show reference solution",
        requested_level=GuidanceLevel.DEBUGGING,
        allow_solution=True,
    )
    assert "complete solution reference" in solution_msg.content.lower()


def test_developer_report_generator() -> None:
    dev_id = f"report_dev_{uuid.uuid4().hex[:6]}"
    developer_repo.ensure_developer(developer_id=dev_id, name="Report Test Dev")

    report = report_generator.generate_report(
        developer_id=dev_id,
        period_type="weekly",
    )
    assert report.developer_id == dev_id
    assert report.period_type == "weekly"
    assert report.content["summary"]["headline"]
    assert isinstance(report.metrics, dict)
    assert "assigned_tasks" in report.metrics
    assert "learning_consistency_percentage" in report.metrics


@pytest.mark.anyio
async def test_mcp_service_and_security_defense() -> None:
    # 1. List tools
    tools = mcp_service.list_tools()
    tool_names = {t.name for t in tools}
    assert "get_developer_task" in tool_names
    assert "read_project_file" in tool_names
    assert "search_knowledge_docs" in tool_names
    assert "submit_task_evaluation" in tool_names
    assert "get_developer_report" in tool_names

    # 2. Path traversal attack defense
    traversal_result = await mcp_service.execute_tool(
        tool_name="read_project_file",
        arguments={"file_path": "../../../../../windows/system32/cmd.exe"},
        caller_id="tester",
    )
    assert traversal_result.status == "error"
    assert traversal_result.error is not None
    error_str = traversal_result.error.lower()
    assert "traversal" in error_str or "blocked" in error_str

    # 3. Read valid project file
    valid_read = await mcp_service.execute_tool(
        tool_name="read_project_file",
        arguments={"file_path": "pyproject.toml"},
        caller_id="tester",
    )
    assert valid_read.status == "success"
    assert valid_read.data is not None
    assert "prism-ide" in valid_read.data["content"]

    # 4. Audit logging verification
    audits = task_platform_repo.get_mcp_audits(caller_id="tester")
    assert len(audits) >= 2


def test_platform_rest_api_end_to_end() -> None:
    dev_id = f"api_test_dev_{uuid.uuid4().hex[:6]}"
    task_id = f"api_test_task_{uuid.uuid4().hex[:6]}"

    # 1. Register dev
    reg = client.post(
        "/auth/register",
        json={
            "email": f"{dev_id}@example.com",
            "password": "Password12345!",
            "name": "Integration Dev",
            "developer_id": dev_id,
        },
    )
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/auth/me", headers=auth_headers)
    assert me_res.status_code == 200
    assert me_res.json()["developer_id"] == dev_id

    # 2. Create task
    task = PersonalizedTask(
        task_id=task_id,
        developer_id=dev_id,
        target_skill="fastapi_basics",
        reason="Foundational API architecture",
        title="Build Health Check",
        description="Create an endpoint returning server status",
        difficulty=TaskDifficulty.BEGINNER,
        priority=TaskPriority.MEDIUM,
        estimated_minutes=60,
        status=TaskStatus.GENERATED,
        requirements=["Return JSON status healthy"],
    )
    intelligence_repo.save_task(task)

    # 3. Assign task via API
    assign_res = client.post(
        f"/tasks/{task_id}/assign",
        json={"developer_id": dev_id},
    )
    assert assign_res.status_code == 200
    assert assign_res.json()["status"] == TaskStatus.ACCEPTED.value

    # 4. Submit task solution via API
    submit_res = client.post(
        f"/tasks/{task_id}/submit",
        json={
            "developer_id": dev_id,
            "submission_type": "code",
            "source_code": "def health(check: bool = True) -> dict:\n    '''Health probe.'''\n    try:\n        return {'status': 'healthy'}\n    except Exception:\n        return {'status': 'error'}\n",
            "explanation": "FastAPI health function with error handling and types",
        },
    )
    assert submit_res.status_code == 200
    sub_id = submit_res.json()["submission_id"]

    # 5. Evaluate submission via API
    eval_res = client.post(f"/evaluation/submissions/{sub_id}")
    assert eval_res.status_code == 200
    eval_data = eval_res.json()
    assert eval_data["submission_id"] == sub_id
    assert eval_data["score"] >= 60.0

    # 6. Start mentoring conversation via API
    conv_res = client.post(
        "/mentoring/conversations/start",
        json={
            "developer_id": dev_id,
            "task_id": task_id,
            "initial_query": "How do I test my health endpoint?",
        },
    )
    assert conv_res.status_code == 200
    conv_id = conv_res.json()["conversation"]["conversation_id"]

    # 7. Request progressive hint via API
    hint_res = client.post(f"/mentoring/conversations/{conv_id}/hint")
    assert hint_res.status_code == 200
    assert "hint" in hint_res.json()["content"].lower()

    # 8. Check Progress Dashboard API
    dash_res = client.get(f"/progress/{dev_id}/dashboard")
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert dash_data["developer_id"] == dev_id
    assert dash_data["total_assigned_tasks"] >= 1

    # 9. Generate Report API
    report_res = client.post(
        "/reports/generate",
        json={"developer_id": dev_id, "period_type": "weekly"},
    )
    assert report_res.status_code == 200
    assert report_res.json()["developer_id"] == dev_id

    # 10. MCP API execution
    mcp_res = client.post(
        "/mcp/tools/execute",
        json={
            "tool_name": "get_developer_task",
            "arguments": {"task_id": task_id},
            "caller_id": dev_id,
        },
    )
    assert mcp_res.status_code == 200
    assert mcp_res.json()["status"] == "success"
