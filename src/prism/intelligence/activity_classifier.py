from typing import Any

from prism.intelligence.languages.registry import (
    LanguageAdapterRegistry,
    language_registry,
)
from prism.intelligence.models.activity_classification_models import (
    ActivityCategory,
    ActivityClassification,
)
from prism.logging.logger import get_logger

logger = get_logger(__name__)


EVENT_CATEGORY_MAP: dict[str, ActivityCategory] = {
    "file_create": ActivityCategory.CODING,
    "file_edit": ActivityCategory.CODING,
    "file_modify": ActivityCategory.CODING,
    "file_open": ActivityCategory.GENERAL,
    "file_delete": ActivityCategory.CODING,
    "code_edit": ActivityCategory.CODING,
    "function_create": ActivityCategory.CODING,
    "class_create": ActivityCategory.CODING,
    "component_create": ActivityCategory.CODING,
    "refactor": ActivityCategory.REFACTORING,
    "import_add": ActivityCategory.DEPENDENCY,
    "import_remove": ActivityCategory.DEPENDENCY,
    "syntax_error": ActivityCategory.DEBUGGING,
    "runtime_error": ActivityCategory.DEBUGGING,
    "error": ActivityCategory.DEBUGGING,
    "debug": ActivityCategory.DEBUGGING,
    "test_run": ActivityCategory.TESTING,
    "test_failure": ActivityCategory.TESTING,
    "test_success": ActivityCategory.TESTING,
    "project_analysis": ActivityCategory.ARCHITECTURE,
    "ai_help": ActivityCategory.GENERAL,
}


class ActivityClassificationEngine:
    """Classifies developer activities into programming concepts, frameworks, and skills."""

    def __init__(self, registry: LanguageAdapterRegistry | None = None) -> None:
        self.registry = registry or language_registry

    def classify(
        self,
        event_type: str,
        file_path: str | None = None,
        code_snippet: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ActivityClassification:
        """Classify an activity with semantic concepts, framework, and language."""
        metadata = metadata or {}

        # 1. Category Detection
        normalized_event = event_type.lower().strip()
        category = EVENT_CATEGORY_MAP.get(normalized_event, ActivityCategory.GENERAL)

        # 2. Language Detection
        detected_language = metadata.get("language")
        if not detected_language:
            detected_language = self.registry.detect_language(file_path, code_snippet)

        adapter = self.registry.get_adapter_for_file(file_path or "", code_snippet)

        # 3. Analyze code or file path if available
        content = code_snippet or ""
        analysis = adapter.analyze_code(content, file_path or "")

        # 4. Framework Detection
        framework = metadata.get("framework")
        if not framework and analysis.frameworks:
            framework = analysis.frameworks[0]

        # 5. Concept & Subconcept Detection
        concept = "General Programming"
        subconcept: str | None = None
        related_skill: str | None = None
        confidence = 0.80

        if normalized_event in ("class_create", "component_create"):
            if "Component" in (framework or "") or "React" in (framework or ""):
                concept = "Component Architecture"
                subconcept = "Components & State"
                related_skill = f"{framework or 'Frontend'} Components"
                confidence = 0.95
            else:
                concept = "Object-Oriented Programming"
                subconcept = "Class Definition"
                related_skill = f"{detected_language} OOP"
                confidence = 0.95
        elif normalized_event == "function_create":
            concept = "Procedural & Functional Logic"
            subconcept = "Function Definition"
            related_skill = f"{detected_language} Functions"
            confidence = 0.90
        elif normalized_event == "refactor":
            concept = "Software Architecture"
            subconcept = "Code Refactoring"
            related_skill = "Refactoring & Design Patterns"
            confidence = 0.90
        elif category == ActivityCategory.TESTING:
            concept = "Quality Assurance & Testing"
            subconcept = (
                "Unit Testing" if "test" in normalized_event else "Test Execution"
            )
            related_skill = f"{detected_language} Testing"
            confidence = 0.95
        elif category == ActivityCategory.DEBUGGING:
            concept = "Error Diagnostics"
            subconcept = "Exception Handling & Debugging"
            related_skill = "Troubleshooting & Debugging"
            confidence = 0.90
        elif analysis.concepts:
            primary_concept = analysis.concepts[0]
            concept = primary_concept.concept
            subconcept = primary_concept.subconcept
            related_skill = primary_concept.related_skill
            confidence = primary_concept.confidence
        else:
            concept = "General Programming"
            subconcept = "Syntax & Implementation"
            related_skill = f"{detected_language} Fundamentals"

        # 6. Project Component Detection
        project_component = self._detect_project_component(file_path, category)

        # 7. Complexity Estimate
        complexity = metadata.get("complexity") or analysis.complexity

        return ActivityClassification(
            category=category,
            language=detected_language,
            framework=framework,
            concept=concept,
            subconcept=subconcept,
            related_skill=related_skill,
            project_component=project_component,
            complexity_estimate=complexity,
            confidence_score=round(confidence, 2),
        )

    def _detect_project_component(
        self, file_path: str | None, category: ActivityCategory
    ) -> str:
        """Infer high-level architecture component from path and category."""
        if not file_path:
            return "general"

        normalized = file_path.lower().replace("\\", "/")

        if "test" in normalized or category == ActivityCategory.TESTING:
            return "testing"
        if any(
            seg in normalized
            for seg in ("ui/", "components/", "frontend/", "views/", "pages/")
        ):
            return "frontend"
        if any(
            seg in normalized
            for seg in (
                "api/",
                "backend/",
                "services/",
                "controllers/",
                "server/",
                "src/main/java",
                "pkg/",
                "internal/",
            )
        ):
            return "backend"
        if any(
            seg in normalized for seg in ("db/", "database/", "migrations/", "models/")
        ):
            return "database"
        if any(seg in normalized for seg in ("android/", "ios/", "mobile/")):
            return "mobile"
        if any(seg in normalized for seg in ("config/", ".github/", "docker", "k8s/")):
            return "configuration"

        if normalized.endswith((".java", ".go", ".cs", ".rs", ".py", ".rb", ".php")):
            return "backend"
            return "configuration"

        return "core"
