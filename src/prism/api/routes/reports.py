from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from prism.api.dependencies import report_generator
from prism.intelligence.models.task_platform_models import (
    DeveloperReport,
)
from prism.logging.logger import get_logger
from prism.security import get_optional_current_user, verify_developer_ownership

logger = get_logger(__name__)

router = APIRouter(prefix="/reports", tags=["Progress Reports"])


class GenerateReportRequest(BaseModel):
    developer_id: str = Field(..., min_length=1)
    period_type: str = Field(
        default="weekly", description="daily, weekly, monthly, custom"
    )
    start_date: datetime | None = None
    end_date: datetime | None = None


@router.post("/generate", response_model=DeveloperReport)
async def generate_progress_report(
    request: GenerateReportRequest,
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> DeveloperReport:
    """Generate, compute, and persist a comprehensive progress report based on real database records."""
    verify_developer_ownership(request.developer_id, current_user)
    try:
        return report_generator.generate_report(
            developer_id=request.developer_id,
            period_type=request.period_type,
            start_date=request.start_date,
            end_date=request.end_date,
        )
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    except Exception as err:
        logger.exception("Failed to generate report for %s", request.developer_id)
        raise HTTPException(
            status_code=500, detail="Internal server error generating report"
        ) from err


@router.get("/{report_id}", response_model=DeveloperReport)
async def get_report(
    report_id: str,
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> DeveloperReport:
    """Retrieve an existing progress report by report ID."""
    report = report_generator.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found")
    verify_developer_ownership(report.developer_id, current_user)
    return report


@router.get("/developer/{developer_id}", response_model=list[DeveloperReport])
async def list_developer_reports(
    developer_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> list[DeveloperReport]:
    """Retrieve historical progress reports for a developer in reverse chronological order."""
    cleaned_id = developer_id.strip()
    verify_developer_ownership(cleaned_id, current_user)
    return report_generator.list_reports(
        developer_id=cleaned_id, limit=limit, offset=offset
    )
