import re
import time
import uuid

from prism.intelligence.models.developer_identity_models import (
    DeveloperIdentificationRequest,
    DeveloperProfile,
    DeveloperRegistrationRequest,
    DeveloperUpdateRequest,
)
from prism.logging.logger import get_logger
from prism.storage.repositories.base import DeveloperRepository

logger = get_logger(__name__)

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class DeveloperIdentityService:
    """Service governing developer registration, identification, and profile management."""

    def __init__(self, developer_repo: DeveloperRepository) -> None:
        self.developer_repo = developer_repo

    def register_developer(
        self, request: DeveloperRegistrationRequest
    ) -> DeveloperProfile:
        """Register a new developer with unique identity attributes."""
        start_time = time.perf_counter()

        cleaned_id = (
            request.developer_id.strip()
            if request.developer_id
            else f"dev_{uuid.uuid4().hex[:12]}"
        )
        if not cleaned_id:
            raise ValueError("Developer ID cannot be empty")

        cleaned_name = request.name.strip() if request.name else None
        cleaned_email = request.email.strip().lower() if request.email else None

        if cleaned_email and not EMAIL_REGEX.match(cleaned_email):
            raise ValueError(f"Invalid email address format: '{cleaned_email}'")

        data = self.developer_repo.create_developer(
            developer_id=cleaned_id,
            name=cleaned_name,
            email=cleaned_email,
        )

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "Developer registered successfully | developer_id=%s | duration_ms=%.2f",
            cleaned_id,
            duration_ms,
        )

        return DeveloperProfile(
            developer_id=data["developer_id"],
            name=data["name"],
            email=data["email"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )

    def identify_developer(
        self, request: DeveloperIdentificationRequest
    ) -> DeveloperProfile | None:
        """Resolve a developer identity using stable surrogate ID or email."""
        start_time = time.perf_counter()

        data = None
        lookup_key = ""
        if request.developer_id and request.developer_id.strip():
            lookup_key = f"id:{request.developer_id.strip()}"
            data = self.developer_repo.get_developer(request.developer_id.strip())
        elif request.email and request.email.strip():
            lookup_key = f"email:{request.email.strip().lower()}"
            data = self.developer_repo.get_by_email(request.email.strip())
        else:
            raise ValueError(
                "Either developer_id or email must be provided for identification"
            )

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "Developer identity resolution completed | lookup=%s | found=%s | duration_ms=%.2f",
            lookup_key,
            data is not None,
            duration_ms,
        )

        if data is None:
            return None

        return DeveloperProfile(
            developer_id=data["developer_id"],
            name=data["name"],
            email=data["email"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )

    def get_profile(self, developer_id: str) -> DeveloperProfile:
        """Retrieve developer profile by ID."""
        cleaned_id = developer_id.strip()
        data = self.developer_repo.get_developer(cleaned_id)
        if data is None:
            raise ValueError(f"Developer not found: '{cleaned_id}'")

        return DeveloperProfile(
            developer_id=data["developer_id"],
            name=data["name"],
            email=data["email"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )

    def update_profile(
        self, developer_id: str, request: DeveloperUpdateRequest
    ) -> DeveloperProfile:
        """Update permitted profile attributes of an existing developer."""
        cleaned_id = developer_id.strip()
        cleaned_name = request.name.strip() if request.name else None
        cleaned_email = request.email.strip().lower() if request.email else None

        if cleaned_email and not EMAIL_REGEX.match(cleaned_email):
            raise ValueError(f"Invalid email address format: '{cleaned_email}'")

        data = self.developer_repo.update_developer(
            developer_id=cleaned_id,
            name=cleaned_name,
            email=cleaned_email,
        )
        if data is None:
            raise ValueError(f"Developer not found: '{cleaned_id}'")

        logger.info("Developer profile updated | developer_id=%s", cleaned_id)
        return DeveloperProfile(
            developer_id=data["developer_id"],
            name=data["name"],
            email=data["email"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )
