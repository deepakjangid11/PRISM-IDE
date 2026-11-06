# PRISM — Security Architecture & Vulnerability Audit Report

**Audit Date:** November 2026
**Auditor:** Principal Security Engineer & QA Auditor
**Scope:** Authentication, Authorization, IDOR, Cryptography, Data Isolation, Filesystem & Injection Attacks

---

## 1. Executive Summary

A comprehensive, adversarial security audit of the PRISM platform was conducted. All attack surfaces—including JWT token lifecycle, password storage, path traversal, IDOR in REST and MCP protocols, SQL injection, and exception leakage—were analyzed and verified with automated test suites.

Zero Critical and Zero High vulnerabilities remain unaddressed in the codebase.

---

## 2. Threat Analysis & Security Controls

### 2.1 Password Security & Cryptographic Storage
- **Mechanism:** Dual-engine password hashing:
  - **Argon2id (OWASP Recommended):** 64 MB memory cost (`m=65536`), 1 iteration (`t=1`), 4 parallel lanes (`p=4`), 16-byte random salt, 32-byte derived key.
  - **PBKDF2-HMAC-SHA256:** 600,000 iterations (NIST SP 800-63B recommendation) with per-user random 16-byte salt.
- **Verification:** Constant-time comparison (`hmac.compare_digest` / `Argon2id.verify`) to neutralize timing attacks.

### 2.2 JWT Authentication & Persistent Revocation
- **Signing Algorithm:** HMAC-SHA256 (`HS256`) using application secret key.
- **Claim Integrity:** Enforces `sub` (developer ID), `role`, `jti` (unique UUID), `iat`, `exp`, and `type`.
- **Revocation Persistence:** Both full tokens and JTIs are tracked in memory and persisted to disk at `.prism/revoked_tokens.json`. Survives server restarts and multi-worker execution.

### 2.3 IDOR (Insecure Direct Object Reference) Protection
- **Vulnerability Addressed:** Preventing developer A from modifying or reading tasks, submissions, evaluations, progress, reports, or analytics belonging to developer B.
- **Implementation:** `verify_developer_ownership(resource_developer_id, current_user)` actively enforced across:
  - `POST /tasks/{task_id}/submit`
  - `POST /tasks/{task_id}/assign`
  - `POST /tasks/{task_id}/evaluate`
  - `GET /tasks/developer/{developer_id}`
  - `GET /evaluation/developer/{developer_id}`
  - `POST /mentoring/conversations/start`
  - `GET /progress/{developer_id}/*`
  - `GET /analytics/*/{developer_id}`
  - `GET /reports/developer/{developer_id}`
  - `POST /mcp/tools/execute` and `POST /mcp/rpc`

### 2.4 Filesystem Security & Path Traversal Prevention
- **Attack Vector:** Callers requesting `../../secret.txt`, `/etc/passwd`, or `C:\Windows\win.ini` through `read_project_file`.
- **Guards:**
  1. Blocks path traversal sequences (`..`).
  2. Blocks Windows volume drive colons (`:`).
  3. Strips leading slashes before resolving.
  4. Enforces `resolved_target.relative_to(workspace_root)`.
  5. Denies sensitive patterns: `.env`, `.git`, `.venv`, `password`, `secret`, `alembic.ini`.
  6. Enforces a 1 MB file read limit.

### 2.5 SQL Injection Defense
- **Implementation:** 100% of database interactions are authored via SQLAlchemy 2.0 ORM expressions and parameterized queries. No raw string interpolation exists.

### 2.6 Safe Evaluation Boundary (Untrusted Code Isolation)
- **Constraint:** Submitted developer code is NEVER executed inside the main FastAPI application runtime.
- **Evaluation Mechanism:** Static AST parsing (`ast.parse`) with strict syntax inspection, structural node checking, and acceptance criteria keyword matching.

---

## 3. Automated Security Verification

The security suite is automatically verified in regression test suites:
- `tests/test_auth_and_security.py` (Password hashing, JWT generation, validation, expiration, and logout revocation)
- `tests/test_qa_security_and_idor.py` (Cross-account IDOR isolation, path traversal denial, and malicious submission containment)
- `tests/test_mcp_protocol_and_server.py` (MCP volume attacks, blocked files, and caller authorization)
