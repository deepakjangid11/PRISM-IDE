# PRISM — AI-Powered Developer Task & Learning Platform

**PRISM (Personalized Real-time Intelligent Skill Mentor)** is an AI-powered developer intelligence and personalized learning platform backend built with Python 3.14, FastAPI, Pydantic, SQLAlchemy, and MySQL.

PRISM acts as an AI technical mentor: diagnosing developer knowledge gaps, assigning practical coding challenges across 5 difficulty levels, providing progressive Socratic guidance across 6 pedagogical levels, evaluating submitted code safely through AST-based static analysis, recording verifiable skill evidence, and exposing standard Model Context Protocol (MCP) tools for external AI agents.

---

## 1. Problem Solved

Traditional developer learning platforms suffer from critical shortcomings:
1. **Generic, Non-Personalized Tasks:** Tutorials assign static exercises unrelated to real-world codebases or the developer's unique knowledge gaps.
2. **All-or-Nothing Answers (The "Copy-Paste Trap"):** When developers get stuck, chatbots dump complete code solutions, undermining deep conceptual retention and critical problem-solving skills.
3. **Unsafe Remote Execution:** Running untrusted code without sandbox infrastructure introduces severe security risks to backend hosts.
4. **Opaque Skill Verification:** Developer resumes and self-reported proficiencies lack verifiable, empirical evidence derived from actual code quality and testing.

PRISM solves these challenges through:
- **Graph-Grounded Skill Profiling:** A directed acyclic graph (DAG) of programming skills and prerequisites mapping canonical software engineering roles.
- **Adaptive Task Recommendation:** Generates tasks dynamically with problem statements, acceptance criteria, test cases, and progressive hints targeting detected skill gaps.
- **6-Level Socratic Mentoring with Anti-Spoiler Guards:** Progresses systematically from High-Level Concepts -> Strategic Approach -> Socratic Hints -> Milestone Steps -> Code Concepts -> Debugging Assistance.
- **Safe Multi-Stage AST Evaluation:** Analyzes syntax trees, modularity, type annotations, and requirements matching deterministically without executing untrusted code on the host process.
- **Verifiable Skill Evidence:** Automatically generates weighted evidence and increments mastery curves upon passing evaluations ($\text{score} \ge 70$).
- **Model Context Protocol (MCP):** Connects external AI tools (Claude Desktop, Cursor, Antigravity) to PRISM workspace tools over official JSON-RPC 2.0 and stdio transports.

---

## 2. System Architecture

```
                              +------------------------------------------------+
                              |              Client Applications               |
                              |   (IDE Extension, Web Client, MCP AI Agents)   |
                              +-----------------------+------------------------+
                                                      | HTTP / JSON-RPC 2.0 / stdio
                                                      v
+---------------------------------------------------------------------------------------------------+
|                                      PRISM BACKEND ENGINE                                         |
|                                                                                                   |
|  +-------------------------------------+      +------------------------------------------------+  |
|  |             API Layer               |      |            Security & Middleware               |  |
|  | - 24 Router Groups                  | <--> | - JWT Bearer Auth (RFC 7519, HS256)            |  |
|  | - 111 Endpoints                     |      | - Persistent Revocation Registry               |  |
|  | - MCP JSON-RPC 2.0 Protocol Handler |      | - Argon2id & PBKDF2 Password Hashing           |  |
|  | - OpenAPI 3.1 & CORS Controls       |      | - IDOR Cross-Account Ownership Guards          |  |
|  +------------------+------------------+      +-----------------------+------------------------+  |
|                     |                                                 |                           |
|                     v                                                 v                           |
|  +---------------------------------------------------------------------------------------------+  |
|  |                                  Core Intelligence Engines                                  |  |
|  |                                                                                             |  |
|  |  +----------------------------+  +----------------------------+  +-----------------------+  |  |
|  |  | Task Recommendation Engine  |  | AST Code Evaluation Engine |  | Guided Mentoring Svc  |  |  |
|  |  | - 5 Difficulty Levels      |  | - Static AST Syntax Parser |  | - 6 Guidance Levels   |  |  |
|  |  | - Role Curriculum Maps     |  | - Criteria Matching        |  | - Progressive Hints   |  |  |
|  |  | - Knowledge Gap Targeting  |  | - Structural Quality Check |  | - Socratic Coaching   |  |  |
|  |  +----------------------------+  +----------------------------+  +-----------------------+  |  |
|  |                                                                                             |  |
|  |  +----------------------------+  +----------------------------+  +-----------------------+  |  |
|  |  | LLM Provider Abstraction   |  | RAG Knowledge Engine       |  | Model Context Protocol|  |  |
|  |  | - Groq, OpenAI, Gemini     |  | - Python AST Chunking      |  | - 6 Registered Tools  |  |  |
|  |  | - Exponential Backoff      |  | - Deterministic Embedding  |  | - JSON Schema Inputs  |  |  |
|  |  | - Secondary Fallback       |  | - Cosine Similarity Store  |  | - Audit Log Tracking  |  |  |
|  |  +----------------------------+  +----------------------------+  +-----------------------+  |  |
|  +----------------------------------------------+----------------------------------------------+  |
|                                                 |                                                 |
|                                                 v                                                 |
|  +---------------------------------------------------------------------------------------------+  |
|  |                                Storage & Persistence Layer                                  |  |
|  |  - SQLAlchemy 2.0 ORM Models & Session Management                                          |  |
|  |  - Repository Pattern: MySQL Implementations & Thread-Safe In-Memory Fallbacks            |  |
|  |  - Alembic Database Migration Chain (0001 -> 0002 -> 0003 -> 0004 Head)                     |  |
|  +----------------------------------------------+----------------------------------------------+  |
+-------------------------------------------------|-------------------------------------------------+
                                                  |
                                                  v
                                      +-----------------------+
                                      |     MySQL 8.0+ DB     |
                                      |      (prism_ide)      |
                                      +-----------------------+
```

---

## 3. Technology Stack

- **Python Runtime:** Python 3.14.7
- **Package & Virtualenv Manager:** `uv`
- **Web API Framework:** FastAPI (ASGI via Uvicorn)
- **Database & ORM:** MySQL 8.0+, SQLAlchemy 2.0+, PyMySQL
- **Database Migrations:** Alembic
- **Settings & Validation:** Pydantic 2.x, Pydantic-Settings
- **Security & Cryptography:** PyJWT, Cryptography (Argon2id, PBKDF2-HMAC-SHA256, HMAC-SHA256)
- **AI & LLM Client:** HTTPX Asynchronous Client, OpenAI-compatible Provider Architecture
- **Model Context Protocol:** MCP Specification `2024-11-05` (Stdio Server & HTTP JSON-RPC 2.0)
- **Quality Assurance & Testing:** Pytest, Pytest-Cov, AnyIO, Ruff, MyPy

---

## 4. Project Directory Structure

```text
PRISM IDE/
├── .env.example                               # Environment variable template
├── .gitignore                                 # Git exclusion rules
├── alembic.ini                                # Alembic migration configuration
├── pyproject.toml                             # Project dependencies and tool settings
├── README.md                                  # Main documentation
├── requirements.txt                           # Synchronized dependency list
├── uv.lock                                    # Deterministic lockfile
├── alembic/
│   ├── env.py                                 # Alembic environment runner
│   └── versions/                              # Migration revisions (0001 through 0004)
├── docs/                                      # Complete technical documentation suite
│   ├── architecture.md                        # Complete system architecture
│   ├── api_documentation.md                   # Endpoint specifications
│   ├── api_inventory.json                     # Discovered OpenAPI endpoint inventory
│   ├── cleanup_report.md                      # Codebase cleanup report
│   ├── database_documentation.md              # MySQL schemas and migrations
│   ├── deployment_guide.md                    # Production deployment guide
│   ├── environment_setup.md                   # Local setup instructions
│   ├── final_audit_report.md                  # Comprehensive Phase 21 audit
│   ├── final_project_report.md                # Final project summary report
│   ├── final_submission_readiness_report.md   # Official readiness checklist
│   ├── mcp_documentation.md                   # Model Context Protocol guide
│   ├── performance_benchmarks.json            # P50/P95 latency benchmark results
│   ├── performance_report.md                  # Performance benchmark report
│   ├── prism_api_postman_collection.json      # Postman v2.1 collection (111 endpoints)
│   ├── prism_postman_environment.json         # Postman environment variables
│   ├── rag_documentation.md                   # RAG architecture documentation
│   ├── security_audit_report.md               # Security & IDOR audit report
│   └── testing_report.md                      # Test suite and coverage report
├── scripts/                                   # QA automation & audit tools
│   ├── api_audit.py                           # Dynamic OpenAPI discovery tool
│   ├── benchmark_performance.py               # Latency & throughput benchmarker
│   ├── generate_postman_collection.py         # Postman collection generator
│   ├── verify_database_crud.py                # Database persistence verifier
│   └── verify_rag_and_mcp.py                  # RAG and MCP integration auditor
├── src/
│   └── prism/
│       ├── __init__.py                        # Package root and version exposition
│       ├── api/                               # FastAPI routing layer
│       │   ├── dependencies.py                # Shared dependency injection singletons
│       │   ├── main.py                        # FastAPI application entrypoint
│       │   └── routes/                        # 19 modular route packages (111 endpoints)
│       ├── config/                            # Environment settings (Pydantic Settings)
│       ├── context/                           # Project workspace scanning
│       ├── evaluation/                        # Safe AST-based code evaluation engine
│       ├── intelligence/                      # Task recommendation & skill graph engines
│       ├── learning/                          # Knowledge gap analyzer & spaced repetition
│       ├── llm/                               # Provider adapters (Groq, OpenAI, Gemini, Mock)
│       ├── logging/                           # Rotating structured logger
│       ├── mcp/                               # MCP service, tools, JSON-RPC, and stdio server
│       ├── mentoring/                         # 6-tier interactive guided learning service
│       ├── project/                           # AST code analyzer and call graph models
│       ├── rag/                               # Code chunker, embeddings, and vector store
│       ├── reporting/                         # Periodic performance report generator
│       ├── security/                          # JWT, Argon2id/PBKDF2, and IDOR validation
│       └── storage/                           # SQLAlchemy models and MySQL repositories
└── tests/                                     # 65 automated test modules (444 tests)
```

---

## 5. Local Setup & Installation

### Prerequisites
- Python 3.14.7 installed.
- `uv` installed (`curl -LsSf https://astral.sh/uv/install.sh | sh` or PowerShell installer).
- MySQL 8.0+ running locally (or use `STORAGE_BACKEND=memory` for offline testing).

### Step 1: Install Dependencies
```bash
uv sync
```

### Step 2: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Key configuration items:
```ini
ENVIRONMENT=development
STORAGE_BACKEND=mysql   # Use 'memory' for offline testing
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=prism_ide
LLM_PROVIDER=mock       # Use 'groq', 'openai', or 'gemini' for real LLM inference
GROQ_API_KEY=your_key_here
```

### Step 3: Run Database Migrations
Apply Alembic migrations to head (`0004`):
```bash
uv run alembic upgrade head
```

### Step 4: Seed Curriculum
```bash
uv run python -m prism.storage.seeder
```

### Step 5: Start Development Server
```bash
uv run uvicorn prism.api.main:app --reload --port 8000
```
API Documentation will be live at `http://localhost:8000/docs`.

---

## 6. Model Context Protocol (MCP) Integration

PRISM features an official implementation of the Model Context Protocol (`2024-11-05`). External AI agents can connect through either:
1. **Stdio Transport:**
   ```bash
   uv run python -m prism.mcp.server
   ```
2. **HTTP JSON-RPC 2.0:**
   Send standard JSON-RPC 2.0 requests (`initialize`, `tools/list`, `tools/call`) to:
   ```http
   POST http://localhost:8000/mcp/rpc
   ```

### Registered Tools
- `get_developer_task`: Retrieve task problem statement, requirements, and progressive hints.
- `read_project_file`: Safe workspace inspection with path traversal and drive volume blocking.
- `get_task_progress`: Query task completion rates and scores with developer ownership verification.
- `search_knowledge_docs`: Semantic search across indexed programming documentation.
- `submit_task_evaluation`: Trigger automated AST analysis on a submission.
- `get_developer_report`: Generate and retrieve periodic progress reports.

---

## 7. Security Architecture

1. **Password Hashing:** Implements OWASP-recommended **Argon2id** (`m=65536, t=1, p=4`) with backward-compatible verification for existing PBKDF2-HMAC-SHA256 hashes.
2. **JWT Lifecycle & Persistent Revocation:** Tokens signed with HMAC-SHA256 (`HS256`). Revoked tokens are tracked in memory and persisted to `.prism/revoked_tokens.json` to survive application restarts and multi-worker execution.
3. **Insecure Direct Object Reference (IDOR) Protection:** Enforces `verify_developer_ownership` across tasks, submissions, evaluations, mentoring dialogues, and analytics.
4. **Filesystem Confinement:** Rejects path traversal sequences (`..`), volume drive qualifiers (`:`), and sensitive files (`.env`, `password`, `secret`).
5. **Safe AST Evaluation:** Untrusted submitted code is never executed directly on the host application process.

---

## 8. Current Limitations & Architectural Boundaries

1. **Host Execution Sandbox:** The code evaluation engine evaluates submissions via deterministic AST static analysis, syntax tree inspection, and acceptance criteria matching. To ensure security, dynamic container-isolated execution (e.g. gVisor or Docker sandboxes) is not executed in the application host process.
2. **Embedding Architecture:** By default, PRISM uses a high-speed, 100% offline deterministic 128-dimensional n-gram token projection provider that requires no GPU or network access. A remote embedding provider is available when OpenAI credentials are provided.
3. **LLM Provider Keys:** When external LLM provider keys (`GROQ_API_KEY`, `OPENAI_API_KEY`) are not provided, PRISM transparently utilizes `MockLLMProvider` for offline development and testing.

---

## 9. Quality Verification & Test Suite

PRISM enforces strict static analysis, complete type safety, and rigorous test coverage.

### Run Ruff Linter:
```bash
uv run ruff check .
```

### Check Code Formatting:
```bash
uv run ruff format --check .
```

### Run MyPy Static Type Checking:
```bash
uv run mypy src tests
```

### Run Full Regression Test Suite with Coverage:
```bash
uv run pytest --cov=src/prism tests/
```

**Results:**
- **Tests Passed:** 445 / 445 (100% pass rate)
- **Total Coverage:** **90%** (8,671 statements)
- **Lint Errors:** 0
- **Type Errors:** 0
