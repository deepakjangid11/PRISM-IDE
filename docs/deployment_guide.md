# PRISM — Production Deployment & Operations Guide

**Target Environment:** Linux / Windows Server / Containerized (Docker, AWS ECS, GCP Cloud Run)
**Process Manager:** Uvicorn with Gunicorn ASGI worker / systemd
**Database:** Managed MySQL 8.0+ (Amazon RDS, Google Cloud SQL, or self-hosted)

---

## 1. System Requirements & Prerequisites

- **Python Runtime:** Python 3.14.7
- **Package Manager:** `uv` (`curl -LsSf https://astral.sh/uv/install.sh | sh` or Windows powershell installer)
- **Database:** MySQL 8.0+ with `utf8mb4` encoding
- **Memory:** Minimum 1 GB RAM (2 GB recommended)
- **Disk Space:** 500 MB for application and runtime virtualenv

---

## 2. Step-by-Step Production Deployment

### Step 1: Clone Repository & Create Virtual Environment
```bash
git clone https://github.com/deepakjangid11/PRISM-IDE.git
cd "PRISM-IDE"
uv sync --frozen
```

### Step 2: Configure Environment Variables
Copy `.env.example` to `.env` and fill in secrets:
```bash
cp .env.example .env
```
Key variables for production:
```ini
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=your_64_char_cryptographically_random_secret_key_here
STORAGE_BACKEND=mysql
DB_HOST=your-mysql-host.internal
DB_PORT=3306
DB_USER=prism_app
DB_PASSWORD=your_strong_mysql_password
DB_NAME=prism_ide
LLM_PROVIDER=groq   # Or 'openai', 'gemini'
GROQ_API_KEY=gsk_...
```

### Step 3: Run Database Migrations
Apply Alembic migrations up to head (`0004`):
```bash
uv run alembic upgrade head
```

### Step 4: Seed Default Curriculum
Seed default skills graph and prerequisite DAG:
```bash
uv run python -m prism.storage.seeder
```

### Step 5: Start Production ASGI Server
Start using Uvicorn with production worker configuration:
```bash
uv run uvicorn prism.api.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --proxy-headers \
  --forwarded-allow-ips "*"
```

---

## 3. Health Checks & Monitoring

- **Liveness & Readiness Endpoint:**
  ```http
  GET /health
  ```
  **Expected Response (200 OK):**
  ```json
  {
    "status": "healthy",
    "timestamp": "2026-11-06T12:00:00Z",
    "version": "0.1.0",
    "database": "connected"
  }
  ```

- **Logging:** Structured rotating logs are emitted to stdout and persisted to `logs/prism.log` (10 MB rotation, 5 backup generations). Read-only environments automatically fall back to stdout without crashing.
