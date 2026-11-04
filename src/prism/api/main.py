from fastapi import FastAPI

from prism.api.routes.developer import router as developer_router
from prism.api.routes.learning import router as learning_router
from prism.api.routes.mentoring import router as mentoring_router
from prism.api.routes.project import router as project_router
from prism.config.settings import Settings

settings = Settings()

app = FastAPI(
    title=settings.app_name,
    description="AI-powered developer intelligence and learning platform.",
    version="0.1.0",
    debug=settings.debug,
)

app.include_router(project_router)
app.include_router(developer_router)
app.include_router(learning_router)
app.include_router(mentoring_router)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "application": settings.app_name,
    }
