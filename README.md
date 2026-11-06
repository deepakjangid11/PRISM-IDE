# PRISM — AI-Powered Developer Task & Learning Platform

**PRISM (Personalized Real-time Intelligent Skill Mentor)** is an AI-powered developer intelligence and personalized learning platform backend built with Python 3.14, FastAPI, Pydantic, and MySQL.

PRISM acts as a personal AI technical mentor: assigning tailored practical development tasks to developers, guiding them progressively when they encounter difficulties, safely evaluating their work, tracking verified skill growth, and generating structured performance reports.

---

## 1. Product Vision & End-to-End Workflow

```
Developer Registration & Profile
               │
               ▼
Skill Profiling & Knowledge Gap Analysis (SkillGraph + SkillTracker)
               │
               ▼
Personalized Coding Task Generation (4 Tiers: Beginner, Elementary, Intermediate, Advanced, Expert)
               │
               ▼
Task Attempt & Interactive AI Guided Mentoring (6 Progressive Levels + Anti-Spoiler Guard)
               │
               ▼
Task Solution Submission (Source Code, File Tree, Git Repos, Explanations)
               │
               ▼
Multi-Stage Safe Evaluation Engine (AST Analysis + Criteria Heuristics + Honest Sandbox Reporting)
               │
               ▼
Verified Skill Evidence Generation (Score >= 70% converts to SkillEvidence)
               │
               ▼
Longitudinal Progress Analytics & Periodic Reporting (Daily, Weekly, Monthly, Custom)
               │
               ▼
Model Context Protocol (MCP) Integration (Secure AI Agent Tools + Persistent Audit Trail)
```

---

## 2. Core Engines & Architecture

### A. Authentication & Security Engine (`prism.security`)
- **Password Security**: Cryptographically secure PBKDF2-HMAC-SHA256 key derivation with 600,000 iterations and 16-byte random cryptographic salt (`prism.security.password`).
- **Token Management**: Strict RFC 7519 HMAC-SHA256 JWT tokens with access and refresh tokens, base64url encoding, and tamper-proof verification (`prism.security.jwt`).
- **Role-Based Access Control (RBAC)**: Enforced via FastAPI dependencies (`get_current_user`, `get_current_active_user`, `require_role`).
- **Endpoints**: `/auth/register`, `/auth/login`, `/auth/logout`, `/auth/refresh`, `/auth/me`.

### B. Personalized Task Generation Engine (`prism.intelligence.task_recommendation_engine`)
- **Tiers**: Categorized across `BEGINNER`, `ELEMENTARY`, `INTERMEDIATE`, `ADVANCED`, and `EXPERT`.
- **Comprehensive Task Specifications**: Each task automatically generates:
  - Concise `title` and overview `description`.
  - Detailed `problem_statement` grounded in real development challenges.
  - Granular `learning_objectives`.
  - Explicit functional and defensive `requirements`.
  - Measurable `acceptance_criteria`.
  - Structured baseline unit `test_cases` with inputs and expected outcomes.
  - Progressive `hints` ordered from high-level intuition to concrete pointers.
  - Expected `expected_deliverables` and multidimensional `evaluation_criteria`.

### C. Interactive AI Guided Learning Engine (`prism.mentoring.guided_learning_service`)
- **6 Progressive Guidance Levels**:
  1. **Level 1 — Conceptual**: Mental models, invariant boundaries, and core design principles.
  2. **Level 2 — Approach**: Architectural decomposition and modular staging strategy.
  3. **Level 3 — Hints**: Targeted, progressive clues that nudge developers without spoiling the solution.
  4. **Level 4 — Step-by-Step**: Task milestone breakdown into actionable, achievable sub-steps.
  5. **Level 5 — Code Concepts**: Illustrative syntax patterns and idiomatic structural examples.
  6. **Level 6 — Debugging**: Root-cause analysis, failure isolation, and error diagnostics.
- **Anti-Spoiler Guard**: Strict protection ensuring reference code implementations are never output unless explicitly permitted (`allow_solution=True`).
- **Stateful Dialogue**: Multi-turn mentoring conversations with full message history persisted in `mentoring_conversations` and `mentoring_messages`.

### D. Task Submission & Safe Evaluation Engine (`prism.evaluation.engine`)
- **Multi-Format Ingestion**: Supports single-file source code, multi-file virtual directory trees, Git repository URLs, and developer architectural explanations.
- **Strict Host Process Safety**: **Never executes untrusted developer code directly inside the host FastAPI application process without container isolation.**
- **Honest Sandbox Capability Reporting**: Automatically audits whether an isolated container runtime is available; if absent, transparently marks dynamic test executions as `skipped_no_sandbox`.
- **Multi-Stage Evaluation**:
  - Stage 1: Static AST validation catching `SyntaxError` and unparseable constructs.
  - Stage 2: Code quality and construct discovery (functions, classes, docstrings, type annotations, defensive `try/except` blocks).
  - Stage 3: Acceptance criteria verification and keyword heuristics.
  - Stage 4: Scoring (0–100) and automated skill evidence generation: any submission with score $\ge 70$ produces verified `SkillEvidence`.

### E. Developer Progress Analytics & Reporting (`prism.reporting.report_generator`)
- **Periodic Scope**: Daily, Weekly, Monthly, and Custom timeframe reports.
- **True Database Metrics**: Aggregated across real task completions, evaluation scores, passing ratios, learning consistency scores, and active study days.
- **Structured Dashboard Outputs**: Pre-formatted JSON schemas ready for UI dashboards, tracking top strengths, critical weaknesses, and personalized recommendations.

### F. Model Context Protocol (MCP) Integration (`prism.mcp.service`)
- **Authorized Tool Registry**:
  - `get_developer_task`: Retrieve task problem statements and requirements.
  - `read_project_file`: Secure workspace inspection with **path traversal defense** blocking `../` escapes.
  - `get_task_progress`: Query developer completion rates, evaluations, and consistency.
  - `search_knowledge_docs`: Semantic RAG search across project documentation.
  - `submit_task_evaluation`: Programmatic submission evaluation for AI agent workflows.
  - `get_developer_report`: Generate and fetch comprehensive developer performance reports.
- **Audit Logging**: Every tool execution is recorded in MySQL `mcp_audit_logs` with execution duration, caller identity, arguments, and outcome status.

---

## 3. Database Schema & Alembic Migrations

PRISM utilizes MySQL 8.0+ managed via Alembic migrations:

- **Revision `0001`**: Core tables (`developers`, `developer_sessions`, `activities`, `skills`, `skill_evidence`, `learning_paths`).
- **Revision `0002`**: Enhanced activity, session, and skill graph tables.
- **Revision `0003`**: Phase 19 tables (`developer_insights`, `developer_feedbacks`, `personalized_tasks`, `task_outcomes`, `mentoring_sessions`, `learning_adaptations`).
- **Revision `0004` (Head — `0004_task_learning_platform`)**:
  - `developers`: Extended with `password_hash`, `role`, and `is_active`.
  - `personalized_tasks`: Extended with `problem_statement`, `learning_objectives_json`, `requirements_json`, `test_cases_json`, `hints_json`, `expected_deliverables_json`, and `evaluation_criteria_json`.
  - `task_submissions`: Developer task solutions (code, file tree, repo, explanation, status).
  - `task_evaluations`: Detailed multi-stage evaluation reports (score, strengths, mistakes, test results, evidence links).
  - `mentoring_conversations`: Stateful mentoring dialogue sessions.
  - `mentoring_messages`: Individual dialogue messages with guidance levels and metadata.
  - `developer_reports`: Periodic performance reports with metrics and content payloads.
  - `mcp_audit_logs`: Audit trail for Model Context Protocol tool invocations.

---

## 4. REST API Endpoint Reference

### Authentication (`/auth`)
- `POST /auth/register`: Register new developer with email and password.
- `POST /auth/login`: Authenticate and receive JWT access and refresh tokens.
- `POST /auth/refresh`: Exchange refresh token for new access token.
- `POST /auth/logout`: Invalidate current developer session.
- `GET /auth/me`: Retrieve profile of currently authenticated developer (`Bearer` token).

### Task Platform & Recommendations (`/tasks`)
- `POST /tasks/generate`: Generate gap-targeted personalized tasks.
- `GET /tasks/recommendations/{developer_id}`: Query recommended tasks for developer.
- `GET /tasks/{task_id}`: Retrieve detailed task specification.
- `POST /tasks/{task_id}/assign`: Accept and assign task to developer.
- `POST /tasks/{task_id}/submit`: Submit solution (code, file tree, repo URL, explanation).
- `GET /tasks/{task_id}/submissions`: List submissions for a specific task.
- `GET /tasks/developer/{developer_id}`: List all tasks assigned to developer.

### Safe Task Evaluation (`/evaluation`)
- `POST /evaluation/submissions/{submission_id}`: Trigger multi-stage evaluation on a submission.
- `GET /evaluation/{evaluation_id}`: Retrieve evaluation report by ID.
- `GET /evaluation/submissions/{submission_id}/result`: Fetch evaluation for a submission.
- `GET /evaluation/developer/{developer_id}`: List evaluations for a developer.

### Interactive Guided Mentoring (`/mentoring`)
- `POST /mentoring/conversations/start`: Start task-linked mentoring conversation.
- `GET /mentoring/conversations/{conversation_id}`: Fetch conversation details.
- `POST /mentoring/conversations/{conversation_id}/message`: Send message at specified guidance level.
- `GET /mentoring/conversations/{conversation_id}/history`: Retrieve full message history.
- `POST /mentoring/conversations/{conversation_id}/hint`: Request next progressive hint (Level 3).
- `POST /mentoring/conversations/{conversation_id}/step-by-step`: Request task milestone breakdown (Level 4).
- `POST /mentoring/conversations/{conversation_id}/debug`: Request error diagnosis assistance (Level 6).

### Progress Analytics & Dashboard (`/progress`)
- `GET /progress/{developer_id}/dashboard`: Executive summary metrics (tasks, scores, consistency, gaps).
- `GET /progress/{developer_id}/skills`: Detailed skill proficiency breakdown and evidence counts.
- `GET /progress/{developer_id}/history`: Chronological progression timeline.
- `GET /progress/{developer_id}/learning-paths`: Active learning paths and completion ratios.

### Performance Reports (`/reports`)
- `POST /reports/generate`: Generate and persist daily, weekly, monthly, or custom report.
- `GET /reports/{report_id}`: Retrieve specific report by ID.
- `GET /reports/developer/{developer_id}`: List generated reports for a developer.

### Model Context Protocol (`/mcp`)
- `GET /mcp/tools`: List all registered, authorized MCP tools and input schemas.
- `POST /mcp/tools/execute`: Execute authorized MCP tool with timing, security checks, and audit logging.
- `GET /mcp/audit`: Query historical MCP tool execution audit logs.

---

## 5. Quality Verification & Testing

PRISM enforces strict static analysis, complete type safety, and rigorous test coverage.

### Run Linting (Ruff)
```powershell
uv run ruff check .
```

### Check Formatting (Ruff)
```powershell
uv run ruff format --check .
```

### Static Type Checking (MyPy)
```powershell
uv run mypy src tests
```

### Run Full Test Suite with Coverage (Pytest)
```powershell
uv run pytest --cov=src/prism tests/
```
*(427 tests passing, 90% total test coverage across all modules)*
