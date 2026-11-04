import uuid
from typing import Protocol

from prism.mentoring.models import (
    MentorContext,
    MentorMode,
    MentorRecommendation,
    MentorResponse,
)


class BaseMentorGenerator(Protocol):
    """Protocol defining the interface for mentor response generation."""

    def generate(self, context: MentorContext) -> MentorResponse:
        """Generate a structured mentor response from the given context."""
        ...


class DeterministicMentorGenerator:
    """Evidence-grounded deterministic mentor response generator.

    Provides high-fidelity guidance for both Build Mode and Learn Mode
    without requiring external LLM dependencies.
    """

    def generate(self, context: MentorContext) -> MentorResponse:
        """Synthesize advice based on verified context."""
        if context.mode == MentorMode.BUILD:
            return self._generate_build_response(context)
        return self._generate_learn_response(context)

    def _generate_build_response(self, context: MentorContext) -> MentorResponse:
        recommendations: list[MentorRecommendation] = []
        actionable_steps: list[str] = []
        evidence_list: list[str] = []

        summary = f"Build Mentoring for query: '{context.query}'"
        explanation_parts = [
            f"Developer '{context.developer_id}' requested build guidance in Build Mode."
        ]

        # 1. Project Intelligence analysis
        if context.project_intelligence:
            summary_info = context.project_intelligence.summary
            evidence_list.append(
                f"Project analyzed: {summary_info.python_files_analyzed} files, "
                f"{summary_info.total_classes} classes, {summary_info.total_dependencies} dependencies."
            )
            explanation_parts.append(
                f"Current project architecture contains {summary_info.total_classes} classes, "
                f"{summary_info.total_functions} functions, and {summary_info.total_dependencies} dependencies."
            )

            # Check dependencies
            ext_deps = summary_info.external_dependencies
            if ext_deps > 0:
                recommendations.append(
                    MentorRecommendation(
                        recommendation_id=str(uuid.uuid4()),
                        category="dependencies",
                        title="Review External Dependencies",
                        details=(
                            f"The project integrates {ext_deps} external dependencies. Ensure all packages "
                            "are strictly pinned and audited for compatibility."
                        ),
                        actionable_steps=[
                            "Inspect requirements in pyproject.toml",
                            "Verify version ranges prevent breaking upstream changes",
                        ],
                        evidence=[f"{ext_deps} external dependencies recorded"],
                    )
                )

            # Check failed files
            if context.project_intelligence.project_context.failed_files:
                failed_count = len(
                    context.project_intelligence.project_context.failed_files
                )
                recommendations.append(
                    MentorRecommendation(
                        recommendation_id=str(uuid.uuid4()),
                        category="code_quality",
                        title="Resolve AST Parsing Failures",
                        details=f"{failed_count} Python files could not be parsed by AST analysis.",
                        actionable_steps=[
                            "Check syntax errors in reported failed files",
                            "Ensure valid UTF-8 encoding across all modules",
                        ],
                        evidence=[f"{failed_count} failed files detected"],
                    )
                )
                actionable_steps.append("Fix syntax errors in unparseable files")

        else:
            explanation_parts.append(
                "No live project structure was provided. Guidance is based on general architecture best practices."
            )

        # 2. Developer behavior habits
        if context.behavior_insights:
            habits = context.behavior_insights.testing_habits
            evidence_list.append(
                f"Behavior telemetry: {context.behavior_insights.total_events} events, "
                f"test frequency {habits.test_frequency:.1%}, error rate {context.behavior_insights.error_rate:.1%}."
            )
            if habits.test_failure_rate >= 0.5:
                recommendations.append(
                    MentorRecommendation(
                        recommendation_id=str(uuid.uuid4()),
                        category="testing",
                        title="Stabilize Failing Tests",
                        details="Frequent test failures detected in recent developer activity sessions.",
                        actionable_steps=[
                            "Run failed tests with verbose output (`pytest -v`)",
                            "Address unit test regressions before implementing new features",
                        ],
                        evidence=[
                            f"Test failure rate at {habits.test_failure_rate:.1%}"
                        ],
                    )
                )
                actionable_steps.append("Stabilize active test suite regressions")

        if not actionable_steps:
            actionable_steps.extend(
                [
                    "Run pytest suite to verify system stability",
                    "Execute ruff lint and format checks",
                    "Review code relationship hierarchy for separation of concerns",
                ]
            )

        return MentorResponse(
            response_id=str(uuid.uuid4()),
            developer_id=context.developer_id,
            mode=MentorMode.BUILD,
            summary=summary,
            explanation=" ".join(explanation_parts),
            recommendations=recommendations,
            actionable_next_steps=actionable_steps,
            context_used={
                "has_project_intelligence": context.project_intelligence is not None,
                "has_behavior_insights": context.behavior_insights is not None,
                "evidence_count": len(evidence_list),
            },
        )

    def _generate_learn_response(self, context: MentorContext) -> MentorResponse:
        recommendations: list[MentorRecommendation] = []
        actionable_steps: list[str] = []
        explanation_parts = [
            f"Learn Mode mentoring for developer '{context.developer_id}'.",
            f"Query: '{context.query}'.",
        ]

        if context.knowledge_gaps:
            explanation_parts.append(
                f"Identified {len(context.knowledge_gaps)} prerequisite knowledge gaps."
            )
            for gap in context.knowledge_gaps:
                recommendations.append(
                    MentorRecommendation(
                        recommendation_id=str(uuid.uuid4()),
                        category="learning",
                        title=f"Address Prerequisite Gap: {gap.missing_skill}",
                        details=gap.description,
                        actionable_steps=[
                            f"Study foundational principles of {gap.missing_skill}",
                            f"Write verifiable exercises and unit tests demonstrating {gap.missing_skill}",
                        ],
                        evidence=[
                            f"Gap type: {gap.gap_type.value}, severity: {gap.severity}"
                        ],
                    )
                )

        if context.learning_path:
            steps_str = " -> ".join(context.learning_path.steps)
            explanation_parts.append(
                f"Recommended structured learning path: {steps_str}."
            )
            for idx, step in enumerate(context.learning_path.steps, 1):
                actionable_steps.append(f"Step {idx}: Study and practice {step}")
        else:
            actionable_steps.extend(
                [
                    "Explore official documentation for the target concept",
                    "Build an isolated prototype project to cement fundamentals",
                    "Write automated test cases validating edge cases",
                ]
            )

        summary = f"Learning roadmap and skill guidance for '{context.query}'"

        return MentorResponse(
            response_id=str(uuid.uuid4()),
            developer_id=context.developer_id,
            mode=MentorMode.LEARN,
            summary=summary,
            explanation=" ".join(explanation_parts),
            recommendations=recommendations,
            actionable_next_steps=actionable_steps,
            context_used={
                "knowledge_gaps_count": len(context.knowledge_gaps),
                "learning_path_steps": (
                    len(context.learning_path.steps) if context.learning_path else 0
                ),
            },
        )
