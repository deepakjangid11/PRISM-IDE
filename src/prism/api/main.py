import time
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from prism.api.routes.activity import router as activity_router
from prism.api.routes.adaptation import router as adaptation_router
from prism.api.routes.analytics import router as analytics_router
from prism.api.routes.auth import router as auth_router
from prism.api.routes.developer import router as developer_router
from prism.api.routes.evaluation import router as evaluation_router
from prism.api.routes.feedback import router as feedback_router
from prism.api.routes.intelligence import router as intelligence_router
from prism.api.routes.learning import router as learning_router
from prism.api.routes.llm import router as llm_router
from prism.api.routes.mcp import router as mcp_router
from prism.api.routes.mentoring import router as mentoring_router
from prism.api.routes.progress import router as progress_router
from prism.api.routes.project import router as project_router
from prism.api.routes.rag import router as rag_router
from prism.api.routes.reports import router as reports_router
from prism.api.routes.session import router as session_router
from prism.api.routes.skills import router as skills_router
from prism.api.routes.tasks import router as tasks_router
from prism.config.settings import Settings
from prism.storage.bootstrap import check_db_connection

settings = Settings()

app = FastAPI(
    title=settings.app_name,
    description="AI-powered developer intelligence and learning platform.",
    version="0.1.0",
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:1420",
        "http://127.0.0.1:1420",
        "tauri://localhost",
        "http://tauri.localhost",
        "https://tauri.localhost",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?|tauri://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_timing_and_request_id(request: Request, call_next) -> Response:
    req_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_sec = time.perf_counter() - start_time
    response.headers["X-Request-ID"] = req_id
    response.headers["X-Process-Time"] = f"{duration_sec:.4f}s"
    return response


app.include_router(auth_router)
app.include_router(project_router)
app.include_router(developer_router)
app.include_router(session_router)
app.include_router(activity_router)
app.include_router(skills_router)
app.include_router(learning_router)
app.include_router(mentoring_router)
app.include_router(intelligence_router)
app.include_router(tasks_router)
app.include_router(evaluation_router)
app.include_router(progress_router)
app.include_router(reports_router)
app.include_router(mcp_router)
app.include_router(analytics_router)
app.include_router(feedback_router)
app.include_router(adaptation_router)
app.include_router(llm_router)
app.include_router(rag_router)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    db_connected = check_db_connection()
    return {
        "status": "healthy",
        "application": settings.app_name,
        "database": "connected" if db_connected else "offline",
    }
