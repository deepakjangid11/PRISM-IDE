from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from prism.context.project_context import build_project_context
from prism.exceptions.custom_exception import CustomException
from prism.intelligence.models.project_intelligence_models import (
    ProjectIntelligence,
)
from prism.intelligence.project_intelligence import (
    build_project_intelligence,
)
from prism.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/projects", tags=["Projects"])


class ProjectAnalysisRequest(BaseModel):
    project_path: str = Field(min_length=1)


@router.post("/analyze")
async def analyze_project(
    request: ProjectAnalysisRequest,
) -> dict[str, Any]:
    """Analyze project structure and Python code."""
    try:
        project_path = Path(request.project_path).expanduser()

        if not project_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Project path does not exist.",
            )

        if not project_path.is_dir():
            raise HTTPException(
                status_code=400,
                detail="Project path must be a directory.",
            )

        logger.info(
            "Project analysis API requested | path=%s",
            project_path,
        )

        result = build_project_context(project_path)

        logger.info(
            "Project analysis API completed | analyzed=%s",
            result["python_files_analyzed"],
        )

        return result

    except HTTPException:
        raise
    except CustomException as error:
        logger.exception("Project analysis API failed")
        raise HTTPException(
            status_code=500,
            detail="Unable to analyze project.",
        ) from error


@router.post("/intelligence")
async def analyze_project_intelligence(
    request: ProjectAnalysisRequest,
) -> dict[str, Any]:
    """Generate complete structural intelligence for a project."""
    try:
        project_path = Path(request.project_path).expanduser()

        if not project_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Project path does not exist.",
            )

        if not project_path.is_dir():
            raise HTTPException(
                status_code=400,
                detail="Project path must be a directory.",
            )

        logger.info(
            "Project intelligence API requested | path=%s",
            project_path,
        )

        result = build_project_intelligence(project_path)

        logger.info(
            "Project intelligence API completed | files=%s",
            result["summary"]["python_files_analyzed"],
        )

        if isinstance(result, ProjectIntelligence):
            return result.model_dump()
        return dict(result)

    except HTTPException:
        raise
    except CustomException as error:
        logger.exception("Project intelligence API failed")
        raise HTTPException(
            status_code=500,
            detail="Unable to generate project intelligence.",
        ) from error
