"""Unit tests for Phase 20 LLM Context Builder and Sensitive Data Scrubbing."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from prism.intelligence.models.developer_intelligence_models import (
    DeveloperInsight,
    DeveloperIntelligenceProfile,
    InsightCategory,
    InsightSeverity,
    PersonalizedTask,
    SkillTrend,
    TaskDifficulty,
    TaskPriority,
    TaskStatus,
    TrendDirection,
)
from prism.intelligence.models.skill_models import (
    DeveloperSkill,
    DeveloperSkillProfile,
    ProficiencyLevel,
)
from prism.learning.models import KnowledgeGap, KnowledgeGapType
from prism.llm.context_builder import LLMContextBuilder, scrub_sensitive_data
from prism.llm.schemas import LLMRole
from prism.mentoring.models import MentoringStrategy


def test_scrub_sensitive_data() -> None:
    raw_text = (
        "Here is my openai key: sk_abcdef1234567890abcdef1234567890 and groq key: "
        "gsk_abcdef1234567890abcdef123456 and gemini: AIzaSyAbcdef1234567890abcdef1234567890.\n"
        "Connect to db using mysql://prism_user:super_secret_password123@localhost:3306/prism_db.\n"
        "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz\n"
        "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0...\n-----END RSA PRIVATE KEY-----"
    )

    scrubbed = scrub_sensitive_data(raw_text)
    assert "sk_abcdef" not in scrubbed
    assert "gsk_abcdef" not in scrubbed
    assert "AIzaSy" not in scrubbed
    assert "super_secret_password123" not in scrubbed
    assert "[REDACTED_API_KEY]" in scrubbed
    assert "[REDACTED_DB_URL]" in scrubbed
    assert "[REDACTED_BEARER_TOKEN]" in scrubbed
    assert "[REDACTED_PRIVATE_KEY]" in scrubbed


def test_build_developer_profile_context() -> None:
    mock_intelligence_engine = MagicMock()
    profile = DeveloperIntelligenceProfile(
        developer_id="dev_100",
        trends={
            "python": SkillTrend(
                skill_name="python",
                current_level="intermediate",
                previous_level="novice",
                direction=TrendDirection.IMPROVING,
                change_description="Improved with recent commits",
            )
        },
        active_gaps=["concurrency", "docker"],
        top_strengths=["python"],
        overall_status="active",
        has_sufficient_data=True,
    )
    mock_intelligence_engine.get_profile.return_value = profile

    builder = LLMContextBuilder(intelligence_engine=mock_intelligence_engine)
    context_str = builder.build_developer_profile_context("dev_100")

    assert "Developer Intelligence Profile" in context_str
    assert "intermediate" in context_str
    assert "concurrency" in context_str
    assert "ACTIVE" in context_str


def test_build_skill_context() -> None:
    mock_skill_tracker = MagicMock()
    dev_skill_profile = DeveloperSkillProfile(developer_id="dev_100")
    dev_skill_profile.skills["fastapi"] = DeveloperSkill(
        developer_id="dev_100",
        skill_name="fastapi",
        proficiency_level=ProficiencyLevel.INTERMEDIATE,
        proficiency_score=75.0,
        evidence_count=8,
        confidence=0.85,
        reasoning="Solid evidence in route creation and middleware.",
    )
    mock_skill_tracker.get_profile.return_value = dev_skill_profile

    mock_gap_analyzer = MagicMock()
    mock_gap_analyzer.identify_gaps.return_value = [
        KnowledgeGap(
            gap_id="gap_1",
            developer_id="dev_100",
            target_skill="fastapi",
            missing_skill="pydantic_v2",
            gap_type=KnowledgeGapType.MISSING_PREREQUISITE,
            severity="medium",
            description="Needs Pydantic V2 migration knowledge",
        )
    ]

    builder = LLMContextBuilder(
        skill_tracker=mock_skill_tracker,
        gap_analyzer=mock_gap_analyzer,
    )
    context_str = builder.build_skill_context("dev_100", target_skill="fastapi")

    assert "Target Skill 'fastapi'" in context_str
    assert "Level=intermediate" in context_str
    assert "Score=75.0/100" in context_str
    assert "pydantic_v2" in context_str


def test_build_error_telemetry_context() -> None:
    mock_intelligence_engine = MagicMock()
    mock_intelligence_engine.get_insights.return_value = [
        DeveloperInsight(
            insight_id="ins_1",
            developer_id="dev_100",
            category=InsightCategory.RECURRING_ERROR,
            severity=InsightSeverity.HIGH,
            title="Async Await Mismatch",
            description="Calling coroutines without await in request handlers.",
            actionable_recommendation="Ensure all async calls are properly awaited.",
        )
    ]

    builder = LLMContextBuilder(intelligence_engine=mock_intelligence_engine)
    context_str = builder.build_error_telemetry_context("dev_100")

    assert "Async Await Mismatch" in context_str
    assert "Calling coroutines without await" in context_str
    assert "Ensure all async calls are properly awaited" in context_str


def test_build_task_context() -> None:
    mock_intelligence_repo = MagicMock()
    mock_intelligence_repo.get_tasks_for_developer.return_value = [
        PersonalizedTask(
            task_id="task_1",
            developer_id="dev_100",
            title="Refactor FastAPI dependencies",
            description="Use yield dependencies for db sessions",
            target_skill="fastapi",
            difficulty=TaskDifficulty.INTERMEDIATE,
            priority=TaskPriority.MEDIUM,
            reason="Architecture refactoring",
            status=TaskStatus.IN_PROGRESS,
        )
    ]

    builder = LLMContextBuilder(intelligence_repo=mock_intelligence_repo)
    context_str = builder.build_task_context("dev_100")

    assert "### Active Practice Tasks" in context_str
    assert "Refactor FastAPI dependencies" in context_str
    assert "in_progress" in context_str


@pytest.mark.parametrize(
    "strategy",
    [
        MentoringStrategy.CONCEPTUAL_EXPLANATION,
        MentoringStrategy.GUIDED_IMPLEMENTATION,
        MentoringStrategy.STEP_BY_STEP_LEARNING,
        MentoringStrategy.DEBUGGING_GUIDANCE,
        MentoringStrategy.PRACTICAL_EXERCISE,
        MentoringStrategy.ADVANCED_TECHNICAL_GUIDANCE,
    ],
)
def test_assemble_mentoring_messages_all_strategies(
    strategy: MentoringStrategy,
) -> None:
    builder = LLMContextBuilder()
    messages = builder.assemble_mentoring_messages(
        developer_id="dev_100",
        query="How do I scale websockets?",
        strategy=strategy,
        explanation_complexity="advanced",
        target_skill="websockets",
        rag_context="File: server.py\n```python\nasync def ws_handler(): pass\n```",
    )

    assert len(messages) == 2
    assert messages[0].role == LLMRole.SYSTEM
    assert messages[1].role == LLMRole.USER
    assert strategy.value in messages[1].content
    assert "Retrieved Project Knowledge (RAG Citations)" in messages[1].content


def test_scrub_sensitive_data_empty() -> None:
    assert scrub_sensitive_data("") == ""
    assert scrub_sensitive_data(None) == ""  # type: ignore[arg-type]


def test_build_developer_profile_context_extended() -> None:
    mock_dev_repo = MagicMock()
    dev_obj = MagicMock()
    dev_obj.primary_role = "Backend Architect"
    dev_obj.experience_level = "senior"
    mock_dev_repo.get_developer.return_value = dev_obj

    mock_intelligence_engine = MagicMock()
    profile = DeveloperIntelligenceProfile(
        developer_id="dev_200",
        trends={},
        active_gaps=[],
        top_strengths=["algorithms", "system-design"],
        critical_weaknesses=["k8s-security", "graphql"],
        overall_status="active",
        has_sufficient_data=True,
    )
    mock_intelligence_engine.get_profile.return_value = profile

    builder = LLMContextBuilder(
        developer_repo=mock_dev_repo,
        intelligence_engine=mock_intelligence_engine,
    )
    ctx = builder.build_developer_profile_context("dev_200")
    assert "Backend Architect" in ctx
    assert "senior" in ctx
    assert "Critical Skill Gaps: k8s-security, graphql" in ctx

    # Test error handling
    mock_intelligence_engine.get_profile.side_effect = RuntimeError("Database offline")
    ctx_err = builder.build_developer_profile_context("dev_200")
    assert "Backend Architect" in ctx_err
    assert "Critical Skill Gaps" not in ctx_err


def test_build_skill_context_missing_and_error() -> None:
    mock_skill_tracker = MagicMock()
    dev_skill_profile = DeveloperSkillProfile(developer_id="dev_300")
    mock_skill_tracker.get_profile.return_value = dev_skill_profile

    builder = LLMContextBuilder(skill_tracker=mock_skill_tracker)
    ctx = builder.build_skill_context("dev_300", target_skill="rust")
    assert "Target Skill 'rust': No verifiable evidence logged yet." in ctx

    # Test error handling
    mock_skill_tracker.get_profile.side_effect = RuntimeError("Skill service timeout")
    ctx_err = builder.build_skill_context("dev_300", target_skill="rust")
    assert "### Skill Competency Evidence" in ctx_err


def test_build_error_telemetry_context_error_handling() -> None:
    mock_intelligence_engine = MagicMock()
    mock_intelligence_engine.get_insights.side_effect = RuntimeError("Engine failure")

    builder = LLMContextBuilder(intelligence_engine=mock_intelligence_engine)
    assert builder.build_error_telemetry_context("dev_300") == ""


def test_build_task_context_empty_and_error() -> None:
    mock_repo = MagicMock()
    mock_repo.get_tasks_for_developer.return_value = []

    builder = LLMContextBuilder(intelligence_repo=mock_repo)
    assert builder.build_task_context("dev_300") == ""

    mock_repo.get_tasks_for_developer.side_effect = RuntimeError("Query error")
    assert builder.build_task_context("dev_300") == ""


def test_assemble_mentoring_messages_with_full_contexts() -> None:
    mock_dev_repo = MagicMock()
    dev = MagicMock()
    dev.primary_role = "Fullstack Engineer"
    dev.experience_level = "intermediate"
    mock_dev_repo.get_developer.return_value = dev

    mock_skill_tracker = MagicMock()
    sp = DeveloperSkillProfile(developer_id="dev_400")
    sp.skills["docker"] = DeveloperSkill(
        developer_id="dev_400",
        skill_name="docker",
        proficiency_level=ProficiencyLevel.BEGINNER,
        proficiency_score=40.0,
    )
    mock_skill_tracker.get_profile.return_value = sp

    mock_intel_engine = MagicMock()
    mock_intel_engine.get_profile.return_value = DeveloperIntelligenceProfile(
        developer_id="dev_400",
        trends={},
        active_gaps=[],
        top_strengths=["python"],
        overall_status="active",
        has_sufficient_data=True,
    )
    mock_intel_engine.get_insights.return_value = [
        DeveloperInsight(
            insight_id="ins_99",
            developer_id="dev_400",
            category=InsightCategory.RECURRING_ERROR,
            severity=InsightSeverity.HIGH,
            title="Container Build OOM",
            description="Exceeding memory limit during multistage build.",
            actionable_recommendation="Use lightweight alpine base image.",
        )
    ]

    mock_intel_repo = MagicMock()
    mock_intel_repo.get_tasks_for_developer.return_value = [
        PersonalizedTask(
            task_id="task_99",
            developer_id="dev_400",
            title="Optimize Dockerfile layers",
            description="Reorder COPY commands",
            target_skill="docker",
            difficulty=TaskDifficulty.INTERMEDIATE,
            priority=TaskPriority.HIGH,
            reason="Build efficiency",
            status=TaskStatus.IN_PROGRESS,
        )
    ]

    builder = LLMContextBuilder(
        developer_repo=mock_dev_repo,
        skill_tracker=mock_skill_tracker,
        intelligence_engine=mock_intel_engine,
        intelligence_repo=mock_intel_repo,
    )

    messages = builder.assemble_mentoring_messages(
        developer_id="dev_400",
        query="How do I optimize Docker image size?",
        strategy=MentoringStrategy.GUIDED_IMPLEMENTATION,
        explanation_complexity="detailed",
        target_skill="docker",
        project_context="FROM python:3.11\nWORKDIR /app",
        rag_context="File: Dockerfile\nCOPY . /app",
    )

    content = messages[1].content
    assert "Fullstack Engineer" in content
    assert "Container Build OOM" in content
    assert "Optimize Dockerfile layers" in content
    assert "Project Context" in content
    assert "Retrieved Project Knowledge" in content
