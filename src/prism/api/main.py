
from fastapi import FastAPI

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


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "application": settings.app_name,
    }
