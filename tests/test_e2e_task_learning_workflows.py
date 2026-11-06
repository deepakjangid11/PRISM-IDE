"""End-to-End Task & Learning Workflows Verification (Workflows A through F).

Verifies the complete developer journey:
- Workflow A: Developer Registration & Initial Skill Assessment
- Workflow B: Personalized Task Recommendation & Status Progression
- Workflow C: Interactive 6-Level Progressive Mentoring & Debugging
- Workflow D: Task Submission & Safe AST Evaluation Engine
- Workflow E: Verifiable Skill Evidence & Gap Re-evaluation
- Workflow F: Performance Report Generation & Progress Dashboard Update
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from prism.api.main import app

client = TestClient(app)


def test_complete_end_to_end_developer_journey() -> None:
    # =========================================================================
    # WORKFLOW A: REGISTRATION & INITIAL SKILL ASSESSMENT
    # =========================================================================
    uid = uuid.uuid4().hex[:8]
    dev_id = f"dev_journey_{uid}"
    email = f"journey_{uid}@prism-learning.org"
    password = "ProductionPassword2026!"

    # 1. Register new developer
    reg_resp = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
            "name": f"Engineer {uid}",
            "developer_id": dev_id,
            "role": "developer",
        },
    )
    assert reg_resp.status_code == 201
    auth_data = reg_resp.json()
    token = auth_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Record initial baseline skill evidence
    ev_resp = client.post(
        "/skills/evidence",
        json={
            "developer_id": dev_id,
            "skill_name": "Python",
            "evidence_type": "implementation",
            "description": "Implemented RESTful CRUD service with Pydantic validation",
            "evidence_strength": 3.0,
            "confidence_score": 0.85,
            "complexity_score": 0.6,
        },
        headers=headers,
    )
    assert ev_resp.status_code == 201

    # 3. Retrieve baseline skill profile
    profile_resp = client.get(f"/skills/profile/{dev_id}", headers=headers)
    assert profile_resp.status_code == 200
    profile = profile_resp.json()
    assert "python" in profile["skills"]

    # =========================================================================
    # WORKFLOW B: PERSONALIZED TASK RECOMMENDATION & ACCEPTANCE
    # =========================================================================
    gen_resp = client.post(
        "/tasks/generate",
        json={
            "developer_id": dev_id,
            "target_role": "Backend Developer",
            "target_goal": "Python",
            "limit": 2,
        },
        headers=headers,
    )
    assert gen_resp.status_code == 200
    tasks = gen_resp.json()
    assert len(tasks) > 0
    assigned_task = tasks[0]
    task_id = assigned_task["task_id"]
    assert assigned_task["title"]
    assert len(assigned_task["learning_objectives"]) >= 1

    # Developer accepts and starts the task (status -> in_progress)
    status_resp = client.patch(
        f"/tasks/{task_id}/status",
        json={"status": "in_progress", "notes": "Starting task implementation"},
        headers=headers,
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "in_progress"

    # =========================================================================
    # WORKFLOW C: INTERACTIVE MENTORING DIALOGUE (6 LEVELS + DEBUG)
    # =========================================================================
    # Start task-linked conversation
    start_conv = client.post(
        "/mentoring/conversations/start",
        json={
            "developer_id": dev_id,
            "task_id": task_id,
            "initial_query": "How should I structure the concurrency queue for this task?",
        },
        headers=headers,
    )
    assert start_conv.status_code == 200
    conv_data = start_conv.json()
    conv_id = conv_data["conversation"]["conversation_id"]
    assert conv_data["first_response"]["content"]

    # Developer asks for progressive hint (Level 3 hint)
    hint_resp = client.post(f"/mentoring/conversations/{conv_id}/hint", headers=headers)
    assert hint_resp.status_code == 200
    hint_msg = hint_resp.json()
    assert hint_msg["guidance_level"] == 3
    assert hint_msg["sender"] == "mentor"

    # Developer asks for step-by-step guidance (Level 4)
    step_resp = client.post(
        f"/mentoring/conversations/{conv_id}/step-by-step", headers=headers
    )
    assert step_resp.status_code == 200
    step_msg = step_resp.json()
    assert step_msg["guidance_level"] == 4

    # Developer requests debug assistance for an error
    debug_resp = client.post(
        f"/mentoring/conversations/{conv_id}/debug",
        json={
            "error_output": "TypeError: object Queue can't be used in 'await' expression",
            "code_snippet": "await asyncio.Queue()",
        },
        headers=headers,
    )
    assert debug_resp.status_code == 200
    debug_msg = debug_resp.json()
    assert debug_msg["guidance_level"] == 6
    assert "debugging" in debug_msg["content"].lower()

    # =========================================================================
    # WORKFLOW D: TASK SUBMISSION & AUTOMATED AST EVALUATION
    # =========================================================================
    solution_code = """
import asyncio

class TaskWorker:
    def __init__(self):
        self.queue = asyncio.Queue()

    async def produce(self, item: str) -> None:
        await self.queue.put(item)

    async def consume(self) -> str:
        return await self.queue.get()
"""
    # 1. Submit solution
    submit_resp = client.post(
        f"/tasks/{task_id}/submit",
        json={
            "developer_id": dev_id,
            "submission_type": "code",
            "source_code": solution_code,
            "explanation": "Implemented clean asynchronous queue producer-consumer pattern.",
        },
        headers=headers,
    )
    assert submit_resp.status_code == 200
    sub_data = submit_resp.json()
    submission_id = sub_data["submission_id"]

    # 2. Evaluate submission using AST engine
    eval_resp = client.post(
        f"/evaluation/submissions/{submission_id}",
        headers=headers,
    )
    assert eval_resp.status_code == 200
    eval_result = eval_resp.json()
    assert eval_result["submission_id"] == submission_id
    assert eval_result["score"] >= 50.0
    assert eval_result["passed"] is True
    assert len(eval_result["test_results"]) > 0

    # =========================================================================
    # WORKFLOW E: SKILL EVIDENCE & KNOWLEDGE GAP RE-EVALUATION
    # =========================================================================
    # Record outcome on task recommendation engine
    eval_task_resp = client.post(
        f"/tasks/{task_id}/evaluate",
        json={
            "developer_id": dev_id,
            "passed": True,
            "score": round(eval_result["score"] / 100.0, 2),
            "execution_notes": "AST static evaluation succeeded with 100% criteria satisfaction.",
        },
        headers=headers,
    )
    assert eval_task_resp.status_code == 200

    # Verify proficiency was updated
    prof_resp = client.get(f"/skills/proficiency/{dev_id}", headers=headers)
    assert prof_resp.status_code == 200
    proficiencies = prof_resp.json()
    assert "python" in proficiencies

    # Verify gaps re-evaluated
    gaps_resp = client.get(f"/skills/gaps/{dev_id}?target_goal=Python", headers=headers)
    assert gaps_resp.status_code == 200

    # =========================================================================
    # WORKFLOW F: REPORT GENERATION & DASHBOARD UPDATE
    # =========================================================================
    # Generate comprehensive report
    rep_resp = client.post(
        "/reports/generate",
        json={
            "developer_id": dev_id,
            "report_type": "comprehensive",
            "period_type": "weekly",
        },
        headers=headers,
    )
    assert rep_resp.status_code == 200
    report = rep_resp.json()
    assert report["developer_id"] == dev_id
    assert "metrics" in report
    assert "content" in report

    # Fetch live progress dashboard
    dash_resp = client.get(f"/progress/{dev_id}/dashboard", headers=headers)
    assert dash_resp.status_code == 200
    dashboard = dash_resp.json()
    assert dashboard["developer_id"] == dev_id
    assert dashboard["total_assigned_tasks"] >= 1
