import sys
from pathlib import Path

from prism.context.project_context import build_project_context
from prism.exceptions.custom_exception import CustomException
from prism.intelligence.code_relationships import analyze_code_relationships
from prism.intelligence.dependency_analyzer import (
    analyze_project_dependencies,
)
from prism.intelligence.models.project_intelligence_models import (
    ProjectContext,
    ProjectIntelligence,
    ProjectIntelligenceSummary,
)
from prism.intelligence.models.relationship_models import (
    CodeRelationshipAnalysis,
)
from prism.logging.logger import get_logger

logger = get_logger(__name__)


def build_project_intelligence(
    project_path: str | Path,
) -> ProjectIntelligence:
    """Build unified structural and dependency intelligence for a project."""
    root = Path(project_path).expanduser().resolve()

    logger.info("Project intelligence started | root=%s", root)

    try:
        context_data = build_project_context(root)
        project_context = ProjectContext.model_validate(context_data)
        dependencies = analyze_project_dependencies(root)

        relationships: list[CodeRelationshipAnalysis] = []

        for file_data in project_context.files:
            relative_path = file_data.file_path
            source_path = root / relative_path

            try:
                source_code = source_path.read_text(encoding="utf-8")

                relationship_data = analyze_code_relationships(
                    source_code,
                    relative_path,
                )

                relationships.append(relationship_data)

            except (OSError, UnicodeDecodeError, ValueError) as error:
                logger.warning(
                    "Relationship analysis failed | file=%s | error=%s",
                    relative_path,
                    error,
                )

        summary = ProjectIntelligenceSummary(
            total_files=project_context.total_files_discovered,
            python_files_analyzed=project_context.python_files_analyzed,
            total_classes=sum(
                len(file_data.classes) for file_data in project_context.files
            ),
            total_functions=sum(
                len(file_data.functions) for file_data in project_context.files
            ),
            total_function_calls=sum(
                len(relationship.function_calls) for relationship in relationships
            ),
            total_dependencies=dependencies.total_dependencies,
            local_dependencies=dependencies.local_dependencies,
            external_dependencies=dependencies.external_dependencies,
        )

        result = ProjectIntelligence(
            project_path=root.as_posix(),
            project_context=project_context,
            dependencies=dependencies,
            code_relationships=relationships,
            summary=summary,
        )

        logger.info(
            "Project intelligence completed | files=%s | functions=%s "
            "| dependencies=%s",
            result.summary.python_files_analyzed,
            result.summary.total_functions,
            result.summary.total_dependencies,
        )

        return result

    except Exception as error:
        logger.exception("Project intelligence generation failed")
        raise CustomException(error, sys) from error
