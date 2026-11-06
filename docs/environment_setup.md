# PRISM — Local Environment & Development Setup Guide

**Target Audience:** Developers, QA Engineers, and System Architects
**Supported Platforms:** Windows 10/11, macOS, Ubuntu / Debian Linux

---

## 1. Quickstart Guide (Under 5 Minutes)

### Step 1: Install `uv`
PRISM uses `uv` for fast, deterministic dependency and environment management.
- **Windows (PowerShell):**
  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
- **macOS / Linux:**
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

### Step 2: Clone & Sync
```bash
git clone https://github.com/deepakjangid11/PRISM-IDE.git
cd "PRISM-IDE"
uv sync
```

### Step 3: Configure Environment
Create `.env` from the template:
```bash
cp .env.example .env
```
For local offline testing without MySQL, you can set:
```ini
STORAGE_BACKEND=memory
LLM_PROVIDER=mock
```
For full database integration:
```ini
STORAGE_BACKEND=mysql
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=prism_ide
```

### Step 4: Run Migrations
```bash
uv run alembic upgrade head
```

### Step 5: Start Development Server
```bash
uv run uvicorn prism.api.main:app --reload --port 8000
```
Open interactive documentation: `http://localhost:8000/docs`.

---

## 2. Running Quality & Verification Checks

### Run All Regression Tests with Coverage:
```bash
uv run pytest --cov=src/prism tests/
```

### Run Ruff Code Quality Checks:
```bash
uv run ruff check .
uv run ruff format --check .
```

### Run MyPy Static Type Checking:
```bash
uv run mypy src tests
```

### Run Full Verification Script Suite:
```bash
uv run python scripts/verify_database_crud.py
uv run python scripts/verify_rag_and_mcp.py
uv run python scripts/benchmark_performance.py
uv run python scripts/api_audit.py
```
