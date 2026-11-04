from fastapi import APIRouter, HTTPException

from prism.api.dependencies import mentoring_engine
from prism.exceptions.custom_exception import CustomException
from prism.logging.logger import get_logger
from prism.mentoring.models import MentorRequest, MentorResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/mentoring", tags=["Mentoring"])


@router.post("/request", response_model=MentorResponse)
async def request_mentoring(request: MentorRequest) -> MentorResponse:
    """Submit a mentoring query in Build Mode or Learn Mode."""
    try:
        logger.info(
            "API request: mentoring | dev=%s | mode=%s",
            request.developer_id,
            request.mode.value,
        )
        return mentoring_engine.mentor(request)
    except ValueError as err:
        logger.warning("Mentoring validation error: %s", err)
        raise HTTPException(status_code=400, detail=str(err)) from err
    except CustomException as err:
        logger.exception("Mentoring engine encountered unexpected failure")
        raise HTTPException(
            status_code=500, detail="Internal server error generating mentor response"
        ) from err
