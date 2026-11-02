
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from prism.context.project_context import build_project_context
from prism.exceptions.custom_exception import CustomException
from prism.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/projects", tags=["Projects"])


class ProjectAnalysisRequest(BaseModel):
    project_path: str = Field(min_length=1)


@router.post("/analyze")
async def analyze_project(
    request: ProjectAnalysisRequest,
) -> dict[str, Any]:
    """Analyze a local project and return its structural context."""
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
