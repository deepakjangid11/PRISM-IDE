# PRISM — System Architecture Documentation

**System:** PRISM (Personalized Real-time Intelligent Skill Mentor)
**Date:** November 2026
**Status:** Verified & Production Ready

---

## 1. High-Level Architecture Overview

PRISM is an AI-powered Developer Task & Adaptive Learning Platform designed to provide contextual mentoring, progressive coding task recommendations, AST-based static code evaluation, and verifiable skill progression tracking.

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
|  | - 110 Endpoints                     |      | - Persistent Revocation Registry               |  |
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

## 2. Component Subsystems

### 2.1 API & Communication Layer
- **Framework:** FastAPI with asynchronous ASGI execution (`uvicorn`).
- **Endpoint Structure:** Modular routers grouped under `src/prism/api/routes/`:
  - `auth`: Registration, login, token refresh, token revocation (`/auth/logout`), and profile retrieval.
  - `tasks`: Task generation, recommendation, assignment, status transition, and submission.
  - `evaluation`: Automated multi-stage submission evaluation and scoring.
  - `mentoring`: Interactive conversations with 6 pedagogical guidance levels.
  - `progress`: High-level metrics dashboard, skill progress, and learning paths.
  - `reports`: Daily, weekly, monthly, and custom learning reports.
  - `mcp`: Tool listing, tool execution, and official JSON-RPC 2.0 protocol endpoint (`/mcp/rpc`).
  - `rag`: Source indexing, project scanning, semantic search, and collection stats.
  - `skills`: Skill graph hierarchy, prerequisites, related concepts, and proficiency tracking.
  - `developer` & `session`: Identity, session lifecycle, and heartbeat tracking.
  - `activity`: Granular keystroke, file change, and language distribution tracking.
  - `analytics`: Longitudinal performance metrics, improvement trends, and snapshots.

### 2.2 Security Architecture
- **JWT Authentication:** Signed with HMAC-SHA256 (`HS256`). Tokens include unique `jti` UUIDs, expiration timestamps, and roles.
- **Revocation Registry:** Dual-layer token revocation checking in-memory cache and atomic `.prism/revoked_tokens.json` file.
- **Password Hashing:** OWASP-compliant Argon2id (64MB memory, 1 iteration, 4 lanes, 32-byte key) with backward-compatible verification for PBKDF2-HMAC-SHA256 (600,000 iterations).
- **IDOR Protection:** `verify_developer_ownership` middleware ensures developers can only access their own tasks, submissions, evaluations, mentoring dialogues, and analytics.

### 2.3 Task Recommendation Engine
- **Difficulty Levels:**
  1. Beginner
  2. Elementary
  3. Intermediate
  4. Advanced
  5. Expert
- **Curriculum Mapping:** Maps canonical roles (Backend Developer, Frontend Developer, Fullstack Engineer, DevOps Engineer, Data Engineer) to skill hierarchies and prerequisites.
- **Adaptation:** Automatically identifies skill gaps and generates targeted tasks with clear problem statements, acceptance criteria, and progressive hints.

### 2.4 Code Evaluation Engine
- **Methodology:** Multi-stage static and AST analysis without executing untrusted code in the application host process:
  1. *Stage 1:* Python AST syntax parsing and syntax error isolation.
  2. *Stage 2:* Structural modularity check (functions, classes, error handling, type annotations).
  3. *Stage 3:* Acceptance criteria keyword and pattern matching.
  4. *Stage 4:* Architectural explanation verification.
- **Skill Evidence:** Automatically records `SkillEvidence` with complexity and strength multipliers when tasks pass evaluation (score >= 70%).

### 2.5 Guided Mentoring Service
- **Pedagogical Progression (6 Levels):**
  1. *Conceptual:* Core computing principles and mental models.
  2. *Approach:* Architectural design patterns and algorithmic strategies.
  3. *Hints:* Socratic clues directing focus to specific logic.
  4. *Step-by-Step:* Actionable procedural milestone breakdown.
  5. *Code Concepts:* Targeted syntax patterns and isolated examples.
  6. *Debugging:* Failure diagnosis, error tracing, and edge-case analysis.

### 2.6 Model Context Protocol (MCP) Server
- **Specification:** Complies with MCP specification `2024-11-05`.
- **Transports:**
  - *Standard Stdio:* Run via `python -m prism.mcp.server`.
  - *HTTP JSON-RPC:* Accessible at `POST /mcp/rpc`.
- **Tools (6):** `get_developer_task`, `read_project_file`, `get_task_progress`, `search_knowledge_docs`, `submit_task_evaluation`, `get_developer_report`.
- **Access Controls:** Restricted file extensions, path traversal blocking outside workspace root, volume qualifier blocking, and caller ownership enforcement.

### 2.7 RAG Knowledge Engine
- **Chunking:** AST chunking for Python files preserving functional boundaries; sliding-window chunking for documentation and other formats.
- **Embeddings:** Deterministic 128-dimensional n-gram token projection provider (100% offline, reproducible) and remote embedding provider interface.
- **Vector Store:** In-memory vector store with cosine similarity calculation and atomic persistence to `.prism/rag_store.json`.
