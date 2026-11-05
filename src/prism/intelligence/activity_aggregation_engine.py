from collections import Counter
from datetime import UTC, datetime, timedelta

from prism.intelligence.models.activity_classification_models import (
    ActivitySummaryResponse,
    CategoryDistributionItem,
    ConceptDistributionItem,
    FrameworkDistributionItem,
    LanguageDistributionItem,
)
from prism.intelligence.models.developer_behavior_models import DeveloperActivity
from prism.logging.logger import get_logger

logger = get_logger(__name__)


class ActivityAggregationEngine:
    """Aggregates developer activity streams into structured analytics and distributions."""

    def aggregate_summary(
        self,
        activities: list[DeveloperActivity],
        developer_id: str,
        project_path: str | None = None,
        time_window: str = "all",
    ) -> ActivitySummaryResponse:
        """Generate comprehensive activity metrics, distributions, and frequencies."""
        filtered = self._filter_by_window(activities, time_window)

        total = len(filtered)
        if total == 0:
            return ActivitySummaryResponse(
                developer_id=developer_id,
                project_path=project_path,
                total_activities=0,
                categories=[],
                languages=[],
                frameworks=[],
                concepts=[],
                error_frequency=0.0,
                debugging_frequency=0.0,
                testing_frequency=0.0,
                refactoring_frequency=0.0,
                time_window=time_window,
            )

        cat_counts: Counter[str] = Counter()
        lang_counts: Counter[str] = Counter()
        fw_counts: Counter[str] = Counter()
        concept_counts: Counter[str] = Counter()

        error_events = 0
        debug_events = 0
        test_events = 0
        refactor_events = 0

        for a in filtered:
            ev_type = a.event_type.lower()
            meta = a.metadata or {}
            clf = meta.get("classification", {})

            cat = clf.get("category") or "general"
            cat_counts[cat] += 1

            lang = clf.get("language") or meta.get("language") or "Unknown"
            lang_counts[lang] += 1

            fw = clf.get("framework") or meta.get("framework")
            if fw:
                fw_counts[fw] += 1

            concept = clf.get("concept")
            if concept:
                concept_counts[concept] += 1

            if ev_type in ("error", "syntax_error", "runtime_error", "test_failure"):
                error_events += 1
            if ev_type in ("debug", "error", "syntax_error", "runtime_error"):
                debug_events += 1
            if "test" in ev_type:
                test_events += 1
            if "refactor" in ev_type:
                refactor_events += 1

        categories = [
            CategoryDistributionItem(
                category=cat,
                count=count,
                percentage=round((count / total) * 100, 2),
            )
            for cat, count in cat_counts.most_common()
        ]

        languages = [
            LanguageDistributionItem(
                language=lang,
                count=count,
                percentage=round((count / total) * 100, 2),
            )
            for lang, count in lang_counts.most_common()
        ]

        frameworks = [
            FrameworkDistributionItem(
                framework=fw,
                count=count,
                percentage=round((count / total) * 100, 2),
            )
            for fw, count in fw_counts.most_common()
        ]

        concepts = [
            ConceptDistributionItem(
                concept=concept,
                count=count,
                percentage=round((count / total) * 100, 2),
            )
            for concept, count in concept_counts.most_common()
        ]

        return ActivitySummaryResponse(
            developer_id=developer_id,
            project_path=project_path,
            total_activities=total,
            categories=categories,
            languages=languages,
            frameworks=frameworks,
            concepts=concepts,
            error_frequency=round(error_events / total, 4),
            debugging_frequency=round(debug_events / total, 4),
            testing_frequency=round(test_events / total, 4),
            refactoring_frequency=round(refactor_events / total, 4),
            time_window=time_window,
        )

    def _filter_by_window(
        self, activities: list[DeveloperActivity], window: str
    ) -> list[DeveloperActivity]:
        if window == "all":
            return activities

        now = datetime.now(UTC)
        cutoff: datetime | None = None

        if window in ("today", "1d"):
            cutoff = now - timedelta(days=1)
        elif window in ("7d", "week"):
            cutoff = now - timedelta(days=7)
        elif window in ("30d", "month"):
            cutoff = now - timedelta(days=30)

        if not cutoff:
            return activities

        result: list[DeveloperActivity] = []
        for a in activities:
            ts = a.timestamp
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            if ts >= cutoff:
                result.append(a)

        return result
