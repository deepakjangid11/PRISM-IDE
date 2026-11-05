import time
import uuid
from datetime import UTC, datetime

from prism.intelligence.activity_aggregation_engine import (
    ActivityAggregationEngine,
)
from prism.intelligence.activity_classifier import (
    ActivityClassificationEngine,
)
from prism.intelligence.developer_session import DeveloperSessionService
from prism.intelligence.models.activity_classification_models import (
    ActivityClassification,
    ActivityIngestRequest,
    ActivityResponse,
    ActivitySummaryResponse,
    BatchActivityIngestRequest,
    LanguageDistributionItem,
    PaginatedActivityResponse,
)
from prism.intelligence.models.developer_behavior_models import DeveloperActivity
from prism.logging.logger import get_logger
from prism.storage.repositories.base import ActivityRepository

logger = get_logger(__name__)


class DeveloperActivityIntelligenceService:
    """Service governing multi-language activity ingestion, classification, and analytics."""

    def __init__(
        self,
        activity_repo: ActivityRepository,
        session_service: DeveloperSessionService | None = None,
        classifier: ActivityClassificationEngine | None = None,
        aggregator: ActivityAggregationEngine | None = None,
    ) -> None:
        self.repo = activity_repo
        self.session_service = session_service
        self.classifier = classifier or ActivityClassificationEngine()
        self.aggregator = aggregator or ActivityAggregationEngine()

    def ingest_activity(self, request: ActivityIngestRequest) -> ActivityResponse:
        """Validate, classify, bind session, and persist a developer activity event."""
        start_time = time.perf_counter()

        # Validation
        dev_id = request.developer_id.strip()
        if not dev_id:
            raise ValueError("developer_id cannot be empty")

        event_type = request.event_type.strip()
        if not event_type:
            raise ValueError("event_type cannot be empty")

        project_path = request.project_path.strip()
        if not project_path:
            raise ValueError("project_path cannot be empty")

        # Session association & validation
        effective_session_id = (
            request.session_id.strip() if request.session_id else None
        )
        if effective_session_id and self.session_service:
            session = self.session_service.get_session(effective_session_id)
            if session and session.developer_id != dev_id:
                raise ValueError(
                    f"Session '{effective_session_id}' belongs to developer '{session.developer_id}', not '{dev_id}'"
                )
        elif not effective_session_id and self.session_service:
            active = self.session_service.get_active_session(dev_id)
            if active:
                effective_session_id = active.session_id

        # Real-time classification
        classification = self.classifier.classify(
            event_type=event_type,
            file_path=request.file_path,
            code_snippet=request.code_snippet,
            metadata=request.metadata,
        )

        event_id = (
            request.event_id.strip()
            if request.event_id
            else f"act_{uuid.uuid4().hex[:12]}"
        )
        now = datetime.now(UTC)

        metadata = dict(request.metadata)
        metadata["classification"] = classification.model_dump()

        activity = DeveloperActivity(
            event_id=event_id,
            developer_id=dev_id,
            session_id=effective_session_id,
            event_type=event_type,
            timestamp=now,
            project_path=project_path,
            file_path=request.file_path,
            metadata=metadata,
        )

        self.repo.save(activity)

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "Developer activity ingested | event_id=%s | dev=%s | session=%s | "
            "event_type=%s | lang=%s | concept=%s | duration_ms=%.2f",
            event_id,
            dev_id,
            effective_session_id,
            event_type,
            classification.language,
            classification.concept,
            duration_ms,
        )

        return ActivityResponse(
            event_id=event_id,
            developer_id=dev_id,
            session_id=effective_session_id,
            event_type=event_type,
            timestamp=now,
            project_path=project_path,
            file_path=request.file_path,
            classification=classification,
            metadata=metadata,
        )

    def batch_ingest(
        self, request: BatchActivityIngestRequest
    ) -> list[ActivityResponse]:
        """Ingest multiple developer activities in a high-throughput batch."""
        start_time = time.perf_counter()
        responses: list[ActivityResponse] = []
        domain_activities: list[DeveloperActivity] = []

        now = datetime.now(UTC)

        for req in request.activities:
            dev_id = req.developer_id.strip()
            event_type = req.event_type.strip()
            project_path = req.project_path.strip()

            effective_session_id = req.session_id.strip() if req.session_id else None
            if not effective_session_id and self.session_service:
                active = self.session_service.get_active_session(dev_id)
                if active:
                    effective_session_id = active.session_id

            classification = self.classifier.classify(
                event_type=event_type,
                file_path=req.file_path,
                code_snippet=req.code_snippet,
                metadata=req.metadata,
            )

            event_id = (
                req.event_id.strip() if req.event_id else f"act_{uuid.uuid4().hex[:12]}"
            )

            metadata = dict(req.metadata)
            metadata["classification"] = classification.model_dump()

            act = DeveloperActivity(
                event_id=event_id,
                developer_id=dev_id,
                session_id=effective_session_id,
                event_type=event_type,
                timestamp=now,
                project_path=project_path,
                file_path=req.file_path,
                metadata=metadata,
            )
            domain_activities.append(act)

            responses.append(
                ActivityResponse(
                    event_id=event_id,
                    developer_id=dev_id,
                    session_id=effective_session_id,
                    event_type=event_type,
                    timestamp=now,
                    project_path=project_path,
                    file_path=req.file_path,
                    classification=classification,
                    metadata=metadata,
                )
            )

        if domain_activities:
            self.repo.save_many(domain_activities)

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "Batch activity ingestion completed | count=%d | duration_ms=%.2f",
            len(domain_activities),
            duration_ms,
        )

        return responses

    def get_history(
        self,
        developer_id: str,
        project_path: str | None = None,
        session_id: str | None = None,
        language: str | None = None,
        category: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedActivityResponse:
        """Retrieve paginated and filtered historical activities for a developer."""
        dev_id = developer_id.strip()
        records, total_count = self.repo.get_history(
            developer_id=dev_id,
            project_path=project_path.strip() if project_path else None,
            session_id=session_id.strip() if session_id else None,
            language=language.strip() if language else None,
            category=category.strip() if category else None,
            limit=limit,
            offset=offset,
        )

        activities: list[ActivityResponse] = []
        for r in records:
            clf_data = r.metadata.get("classification") if r.metadata else None
            classification = (
                ActivityClassification(**clf_data)
                if clf_data
                else self.classifier.classify(
                    r.event_type, r.file_path, metadata=r.metadata
                )
            )
            activities.append(
                ActivityResponse(
                    event_id=r.event_id,
                    developer_id=r.developer_id,
                    session_id=r.session_id,
                    event_type=r.event_type,
                    timestamp=r.timestamp,
                    project_path=r.project_path,
                    file_path=r.file_path,
                    classification=classification,
                    metadata=r.metadata or {},
                )
            )

        return PaginatedActivityResponse(
            developer_id=dev_id,
            total_count=total_count,
            limit=limit,
            offset=offset,
            activities=activities,
        )

    def get_session_activities(self, session_id: str) -> list[ActivityResponse]:
        """Fetch all activities associated with a specific working session."""
        records = self.repo.get_by_session(session_id.strip())
        results: list[ActivityResponse] = []
        for r in records:
            clf_data = r.metadata.get("classification") if r.metadata else None
            classification = (
                ActivityClassification(**clf_data)
                if clf_data
                else self.classifier.classify(
                    r.event_type, r.file_path, metadata=r.metadata
                )
            )
            results.append(
                ActivityResponse(
                    event_id=r.event_id,
                    developer_id=r.developer_id,
                    session_id=r.session_id,
                    event_type=r.event_type,
                    timestamp=r.timestamp,
                    project_path=r.project_path,
                    file_path=r.file_path,
                    classification=classification,
                    metadata=r.metadata or {},
                )
            )
        return results

    def get_activity_summary(
        self,
        developer_id: str,
        project_path: str | None = None,
        time_window: str = "all",
    ) -> ActivitySummaryResponse:
        """Fetch aggregated metrics and distributions for a developer."""
        dev_id = developer_id.strip()
        activities = self.repo.get_by_developer(dev_id, project_path)
        return self.aggregator.aggregate_summary(
            activities=activities,
            developer_id=dev_id,
            project_path=project_path,
            time_window=time_window,
        )

    def get_language_distribution(
        self, developer_id: str, project_path: str | None = None
    ) -> list[LanguageDistributionItem]:
        """Fetch language-wise activity distribution for a developer."""
        summary = self.get_activity_summary(developer_id, project_path)
        return summary.languages
