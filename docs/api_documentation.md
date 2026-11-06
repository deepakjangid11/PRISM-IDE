# PRISM — API Documentation & Integration Guide

**Base URL:** `http://localhost:8000`
**OpenAPI Specification:** Available at `/openapi.json` and interactive Swagger UI at `/docs`
**Total Endpoints:** 111 operations across 110 paths
**Authentication Scheme:** `Bearer <JWT_TOKEN>` (HTTP Authorization header)

---

## 1. Authentication Endpoints (`/auth`)

### 1.1 Register Developer
- **Method:** `POST /auth/register`
- **Request Body:**
  ```json
  {
    "email": "developer@example.com",
    "password": "StrongPassword123!",
    "name": "Alex Mercer",
    "role": "Backend Developer",
    "developer_id": "dev_alex_01"
  }
  ```
- **Response (201 Created):**
  ```json
  {
    "developer_id": "dev_alex_01",
    "email": "developer@example.com",
    "name": "Alex Mercer",
    "role": "Backend Developer",
    "is_active": true,
    "created_at": "2026-11-06T12:00:00Z"
  }
  ```

### 1.2 Login & Token Acquisition
- **Method:** `POST /auth/login`
- **Request Body:**
  ```json
  {
    "email": "developer@example.com",
    "password": "StrongPassword123!"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "expires_in": 3600,
    "developer_id": "dev_alex_01"
  }
  ```

### 1.3 Refresh Access Token
- **Method:** `POST /auth/refresh`
- **Request Body:**
  ```json
  {
    "refresh_token": "eyJhbGciOi..."
  }
  ```
- **Response (200 OK):** Returns fresh `access_token` and `refresh_token`.

### 1.4 Logout & Token Revocation
- **Method:** `POST /auth/logout`
- **Headers:** `Authorization: Bearer <access_token>`
- **Response (200 OK):**
  ```json
  {
    "status": "revoked",
    "message": "Token has been successfully revoked and invalidated across all sessions."
  }
  ```

### 1.5 Get Current Profile
- **Method:** `GET /auth/me`
- **Headers:** `Authorization: Bearer <access_token>`
- **Response (200 OK):** Returns authenticated developer record.

---

## 2. Personalized Tasks API (`/tasks`)

### 2.1 Generate Tasks for Developer
- **Method:** `POST /tasks/generate`
- **Headers:** `Authorization: Bearer <token>`
- **Request Body:**
  ```json
  {
    "developer_id": "dev_alex_01",
    "target_skill": "FastAPI",
    "count": 3
  }
  ```
- **Response (200 OK):** List of generated tasks with problem statements, acceptance criteria, and progressive hints.

### 2.2 Get Task Recommendations
- **Method:** `GET /tasks/recommendations/{developer_id}?limit=5`
- **Headers:** `Authorization: Bearer <token>`
- **Response (200 OK):** Personalized prioritized list of tasks matched to current knowledge gaps.

### 2.3 Assign Task
- **Method:** `POST /tasks/{task_id}/assign`
- **Headers:** `Authorization: Bearer <token>`
- **Request Body:**
  ```json
  {
    "developer_id": "dev_alex_01"
  }
  ```
- **Response (200 OK):** Task status updated to `in_progress`.

### 2.4 Submit Task Work
- **Method:** `POST /tasks/{task_id}/submit`
- **Headers:** `Authorization: Bearer <token>`
- **Request Body:**
  ```json
  {
    "developer_id": "dev_alex_01",
    "submission_type": "code",
    "source_code": "def process(): return True",
    "explanation": "Implemented modular handler with input validation."
  }
  ```
- **Response (200 OK):** Recorded submission metadata with `submission_id`.

---

## 3. Evaluation API (`/evaluation`)

### 3.1 Evaluate Submission
- **Method:** `POST /evaluation/submissions/{submission_id}`
- **Headers:** `Authorization: Bearer <token>`
- **Response (200 OK):**
  ```json
  {
    "evaluation_id": "eval_7a8b9c",
    "submission_id": "sub_123456",
    "task_id": "task_abc",
    "passed": true,
    "score": 85.0,
    "completion_status": "passed",
    "strengths": [
      "Source code successfully passed AST parsing with valid Python syntax.",
      "Defined 1 function(s) and 0 class(es) providing modular structure."
    ],
    "mistakes": [],
    "missing_requirements": [],
    "improvement_suggestions": [
      "Add type annotations to function parameters and return types."
    ],
    "feedback_message": "Congratulations! Your submission passed evaluation...",
    "test_results": [
      {
        "name": "AST Syntax & Structure Validation",
        "passed": true,
        "description": "Code parses cleanly into valid AST nodes without syntax errors."
      }
    ],
    "evaluated_at": "2026-11-06T12:05:00Z"
  }
  ```

---

## 4. Guided Mentoring API (`/mentoring`)

### 4.1 Request Mentoring Session
- **Method:** `POST /mentoring/request`
- **Request Body:**
  ```json
  {
    "developer_id": "dev_alex_01",
    "task_id": "task_abc",
    "query": "How do I implement dependency injection in this endpoint?"
  }
  ```
- **Response (200 OK):** Mentoring advice grounded in project context and developer skill level.

### 4.2 Start Task-Linked Interactive Dialogue
- **Method:** `POST /mentoring/conversations/start`
- **Headers:** `Authorization: Bearer <token>`
- **Request Body:**
  ```json
  {
    "developer_id": "dev_alex_01",
    "task_id": "task_abc",
    "initial_query": "I am stuck on input validation."
  }
  ```
- **Response (200 OK):** Conversation session with unique `conversation_id`.

### 4.3 Request Specific Guidance Levels
- **POST `/mentoring/conversations/{id}/conceptual`:** High-level principles.
- **POST `/mentoring/conversations/{id}/approach`:** Strategic design patterns.
- **POST `/mentoring/conversations/{id}/hints`:** Socratic hints.
- **POST `/mentoring/conversations/{id}/step-by-step`:** Procedural milestones.
- **POST `/mentoring/conversations/{id}/code-concepts`:** Syntax patterns.
- **POST `/mentoring/conversations/{id}/debugging`:** Error troubleshooting.

---

## 5. Model Context Protocol API (`/mcp`)

### 5.1 JSON-RPC 2.0 Protocol Endpoint
- **Method:** `POST /mcp/rpc`
- **Headers:** `Content-Type: application/json`
- **Example Handshake Request:**
  ```json
  {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {"protocolVersion": "2024-11-05"}
  }
  ```
- **Example Tools Call:**
  ```json
  {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "read_project_file",
      "arguments": {"file_path": "README.md"}
    }
  }
  ```

### 5.2 List MCP Tools
- **Method:** `GET /mcp/tools`
- **Response (200 OK):** List of tool definitions and argument schemas.

### 5.3 Execute Tool via REST
- **Method:** `POST /mcp/tools/execute`
- **Request Body:**
  ```json
  {
    "tool_name": "get_developer_task",
    "arguments": {"task_id": "task_123"},
    "caller_id": "dev_alex_01"
  }
  ```

---

## 6. Developer Progress & Reports API (`/progress` & `/reports`)

- **GET `/progress/{developer_id}/dashboard`:** High-level task metrics, success rate, consistency score.
- **GET `/progress/{developer_id}/skills`:** Granular skill masteries and evidence counts.
- **GET `/progress/{developer_id}/learning-paths`:** Current roadmap and milestone status.
- **POST `/reports/generate`:** Generates comprehensive daily, weekly, or monthly progress reports.
- **GET `/reports/developer/{developer_id}`:** Lists previously generated reports.
