"""Unit tests for Phase 20 Adaptive Mentoring Engine with LLM and RAG integration."""

from __future__ import annotations

import pytest

from prism.llm.exceptions import LLMRateLimitError
from prism.llm.providers.mock_provider import MockLLMProvider
from prism.llm.schemas import StreamChunk
from prism.llm.service import LLMService
from prism.mentoring.adaptive_engine import AdaptiveMentoringEngine
from prism.mentoring.models import (
    AdaptiveMentorRequest,
    AdaptiveMentorResponse,
    MentoringStrategy,
)
from prism.rag.embeddings import DeterministicEmbeddingProvider
from prism.rag.service import RAGService
from prism.storage.repositories.memory_repo import InMemoryIntelligenceRepository


@pytest.fixture
def memory_repo() -> InMemoryIntelligenceRepository:
    return InMemoryIntelligenceRepository()


@pytest.fixture
def mock_llm_service() -> LLMService:
    provider = MockLLMProvider(
        default_response=(
            "Pedagogical LLM Guidance:\n"
            "- Step 1: Write an isolated test verifying bug behavior.\n"
            "- Step 2: Fix async awaiting on the call site.\n"
            "- Step 3: Run pytest to confirm zero regressions."
        )
    )
    provider.simulated_latency = 0.0
    return LLMService(provider=provider)


@pytest.fixture
def populated_rag_service() -> RAGService:
    service = RAGService(
        embedding_provider=DeterministicEmbeddingProvider(dimension=64)
    )
    return service


@pytest.mark.anyio
async def test_adaptive_mentoring_async_llm_success(
    memory_repo: InMemoryIntelligenceRepository,
    mock_llm_service: LLMService,
    populated_rag_service: RAGService,
) -> None:
    # Index a code chunk
    await populated_rag_service.index_file(
        "src/api/auth.py",
        "def verify_token(token: str) -> bool:\n    return len(token) > 10\n",
    )

    engine = AdaptiveMentoringEngine(
        intelligence_repo=memory_repo,
        llm_service=mock_llm_service,
        rag_service=populated_rag_service,
    )

    req = AdaptiveMentorRequest(
        developer_id="dev_200",
        query="How to verify JWT token in auth?",
        preferred_strategy=MentoringStrategy.GUIDED_IMPLEMENTATION,
        use_llm=True,
        enable_rag=True,
    )

    res = await engine.request_adaptive_mentoring_async(req)
    assert isinstance(res, AdaptiveMentorResponse)
    assert res.selected_strategy == MentoringStrategy.GUIDED_IMPLEMENTATION
    assert "Pedagogical LLM Guidance" in res.explanation
    assert res.provider_used == "mock"
    assert len(res.retrieved_citations) > 0
    assert "src/api/auth.py" in res.retrieved_citations[0]
    assert len(res.actionable_steps) >= 2


@pytest.mark.anyio
async def test_adaptive_mentoring_offline_fallback_on_llm_error(
    memory_repo: InMemoryIntelligenceRepository,
) -> None:
    # LLM configured to fail
    failing_provider = MockLLMProvider()
    failing_provider.should_fail = True
    failing_provider.failure_exception = LLMRateLimitError("Exceeded API credits")

    failing_service = LLMService(provider=failing_provider)

    engine = AdaptiveMentoringEngine(
        intelligence_repo=memory_repo,
        llm_service=failing_service,
    )

    req = AdaptiveMentorRequest(
        developer_id="dev_200",
        query="Fix index out of range bug",
        preferred_strategy=MentoringStrategy.DEBUGGING_GUIDANCE,
        use_llm=True,
    )

    res = await engine.request_adaptive_mentoring_async(req)
    assert isinstance(res, AdaptiveMentorResponse)
    assert res.provider_used == "deterministic_fallback"
    assert "Diagnostic & Debugging Protocol" in res.explanation
    assert len(res.actionable_steps) > 0


@pytest.mark.anyio
async def test_adaptive_mentoring_use_llm_false(
    memory_repo: InMemoryIntelligenceRepository,
    mock_llm_service: LLMService,
) -> None:
    engine = AdaptiveMentoringEngine(
        intelligence_repo=memory_repo,
        llm_service=mock_llm_service,
    )

    req = AdaptiveMentorRequest(
        developer_id="dev_200",
        query="Teach me basic python decorators",
        use_llm=False,
    )

    res = await engine.request_adaptive_mentoring_async(req)
    assert res.provider_used == "deterministic"
    assert "Guided Implementation Walkthrough:" in res.explanation


@pytest.mark.anyio
async def test_adaptive_mentoring_streaming(
    memory_repo: InMemoryIntelligenceRepository,
    mock_llm_service: LLMService,
) -> None:
    engine = AdaptiveMentoringEngine(
        intelligence_repo=memory_repo,
        llm_service=mock_llm_service,
    )

    req = AdaptiveMentorRequest(
        developer_id="dev_200",
        query="Explain concurrency models",
        preferred_strategy=MentoringStrategy.CONCEPTUAL_EXPLANATION,
        use_llm=True,
    )

    chunks: list[StreamChunk] = []
    async for chunk in engine.request_adaptive_mentoring_stream(req):
        chunks.append(chunk)

    assert len(chunks) > 0
    full_text = "".join(c.delta for c in chunks)
    assert "Pedagogical LLM Guidance" in full_text


def test_adaptive_mentoring_synchronous_compatibility(
    memory_repo: InMemoryIntelligenceRepository,
    mock_llm_service: LLMService,
) -> None:
    engine = AdaptiveMentoringEngine(
        intelligence_repo=memory_repo,
        llm_service=mock_llm_service,
    )

    req = AdaptiveMentorRequest(
        developer_id="dev_200",
        query="How to optimize database queries?",
        preferred_strategy=MentoringStrategy.ADVANCED_TECHNICAL_GUIDANCE,
        use_llm=True,
    )

    res = engine.request_adaptive_mentoring(req)
    assert isinstance(res, AdaptiveMentorResponse)
    assert res.selected_strategy == MentoringStrategy.ADVANCED_TECHNICAL_GUIDANCE
    assert res.provider_used == "mock"


@pytest.mark.anyio
async def test_adaptive_mentoring_stream_simulated_fallback(
    memory_repo: InMemoryIntelligenceRepository,
) -> None:
    # No LLM service configured, exercises simulated streaming
    engine = AdaptiveMentoringEngine(
        intelligence_repo=memory_repo,
        llm_service=None,
    )

    req = AdaptiveMentorRequest(
        developer_id="dev_200",
        query="Explain Python generators",
        use_llm=False,
    )

    chunks: list[StreamChunk] = []
    async for chunk in engine.request_adaptive_mentoring_stream(req):
        chunks.append(chunk)

    assert len(chunks) > 0
    assert any(c.finish_reason == "stop" for c in chunks)
    assert chunks[0].provider == "deterministic"


@pytest.mark.anyio
async def test_adaptive_mentoring_stream_validation(
    memory_repo: InMemoryIntelligenceRepository,
) -> None:
    engine = AdaptiveMentoringEngine(intelligence_repo=memory_repo)

    with pytest.raises(ValueError, match="Developer ID cannot be empty"):
        req = AdaptiveMentorRequest(developer_id="", query="query")
        async for _ in engine.request_adaptive_mentoring_stream(req):
            pass

    with pytest.raises(ValueError, match="Query cannot be empty"):
        req = AdaptiveMentorRequest(developer_id="dev_1", query="")
        async for _ in engine.request_adaptive_mentoring_stream(req):
            pass


@pytest.mark.anyio
async def test_adaptive_mentoring_async_validation(
    memory_repo: InMemoryIntelligenceRepository,
) -> None:
    engine = AdaptiveMentoringEngine(intelligence_repo=memory_repo)

    with pytest.raises(ValueError, match="Developer ID cannot be empty"):
        await engine.request_adaptive_mentoring_async(
            AdaptiveMentorRequest(developer_id="", query="query")
        )

    with pytest.raises(ValueError, match="Query cannot be empty"):
        await engine.request_adaptive_mentoring_async(
            AdaptiveMentorRequest(developer_id="dev_1", query="")
        )


def test_mentoring_models_getitem() -> None:
    from prism.mentoring.models import MentoringSessionRecord

    resp = AdaptiveMentorResponse(
        session_id="s1",
        developer_id="d1",
        selected_strategy=MentoringStrategy.GUIDED_IMPLEMENTATION,
        explanation_complexity="intermediate",
        mentoring_difficulty="intermediate",
        summary="Summary",
        explanation="Explanation",
    )
    assert resp["session_id"] == "s1"
    with pytest.raises(KeyError):
        _ = resp["non_existent_key"]

    record = MentoringSessionRecord(
        session_id="s1",
        developer_id="d1",
        strategy=MentoringStrategy.GUIDED_IMPLEMENTATION,
        query="q",
        summary="sum",
    )
    assert record["session_id"] == "s1"
    with pytest.raises(KeyError):
        _ = record["non_existent_key"]


@pytest.mark.anyio
async def test_adaptive_mentoring_sync_wrapper_in_loop(
    memory_repo: InMemoryIntelligenceRepository,
    mock_llm_service: LLMService,
) -> None:
    engine = AdaptiveMentoringEngine(
        intelligence_repo=memory_repo,
        llm_service=mock_llm_service,
    )
    req = AdaptiveMentorRequest(
        developer_id="dev_sync_loop",
        query="Explain concurrency models",
        use_llm=True,
    )
    # Since we are inside an async test, loop.is_running() is True
    res = engine.request_adaptive_mentoring(req)
    assert res.developer_id == "dev_sync_loop"
    assert "Pedagogical LLM Guidance" in res.explanation


@pytest.mark.anyio
async def test_adaptive_mentoring_resilience_to_subsystem_errors(
    memory_repo: InMemoryIntelligenceRepository,
    mock_llm_service: LLMService,
) -> None:
    from unittest.mock import MagicMock

    mock_intel_engine = MagicMock()
    mock_intel_engine.get_profile.side_effect = RuntimeError("Profile service offline")

    mock_task_engine = MagicMock()
    mock_task_engine.generate_tasks.side_effect = RuntimeError("Task service down")

    mock_rag = MagicMock()
    mock_rag.build_rag_context.side_effect = RuntimeError("RAG index failed")

    mock_repo = MagicMock()
    mock_repo.save_mentoring_session.side_effect = RuntimeError("DB write error")

    engine = AdaptiveMentoringEngine(
        intelligence_repo=mock_repo,
        llm_service=mock_llm_service,
        rag_service=mock_rag,
        intelligence_engine=mock_intel_engine,
        task_engine=mock_task_engine,
    )

    req = AdaptiveMentorRequest(
        developer_id="dev_resilient",
        query="How to design error handling?",
        target_skill="error-handling",
        use_llm=True,
        enable_rag=True,
    )

    res = await engine.request_adaptive_mentoring_async(req)
    assert res.developer_id == "dev_resilient"
    assert "Pedagogical LLM Guidance" in res.explanation


@pytest.mark.anyio
async def test_adaptive_mentoring_stream_error_handling_and_fallback(
    memory_repo: InMemoryIntelligenceRepository,
) -> None:
    from unittest.mock import MagicMock

    failing_provider = MockLLMProvider()
    failing_provider.should_fail = True
    failing_llm = LLMService(provider=failing_provider)

    mock_intel_engine = MagicMock()
    mock_intel_engine.get_profile.side_effect = RuntimeError("Stream profile error")

    mock_rag = MagicMock()
    mock_rag.build_rag_context.side_effect = RuntimeError("Stream RAG error")

    engine = AdaptiveMentoringEngine(
        intelligence_repo=memory_repo,
        llm_service=failing_llm,
        rag_service=mock_rag,
        intelligence_engine=mock_intel_engine,
    )

    req = AdaptiveMentorRequest(
        developer_id="dev_stream_err",
        query="Stream fallback test",
        use_llm=True,
        enable_rag=True,
    )

    chunks: list[StreamChunk] = []
    async for chunk in engine.request_adaptive_mentoring_stream(req):
        chunks.append(chunk)

    # Should have safely fallen back to deterministic/simulated stream
    assert len(chunks) > 0
    assert chunks[0].provider == "deterministic"


def test_adaptive_mentoring_internal_helpers() -> None:
    from prism.intelligence.models.developer_intelligence_models import (
        DeveloperIntelligenceProfile,
        SkillTrend,
        TrendDirection,
    )

    engine = AdaptiveMentoringEngine(intelligence_repo=InMemoryIntelligenceRepository())

    # 1. Target skill in profile trends (proficient)
    prof_profile = DeveloperIntelligenceProfile(
        developer_id="dev_prof",
        trends={
            "python": SkillTrend(
                skill_name="python",
                current_level="proficient",
                previous_level="intermediate",
                direction=TrendDirection.IMPROVING,
                change_description="Level advanced",
            )
        },
        active_gaps=["docker"],
    )
    comp, diff = engine._determine_complexity_and_difficulty(
        strategy=MentoringStrategy.PRACTICAL_EXERCISE,
        target_skill="python",
        profile=prof_profile,
    )
    assert comp == "advanced"
    assert diff == "advanced"

    # 2. Target skill in profile trends (intermediate)
    int_profile = DeveloperIntelligenceProfile(
        developer_id="dev_int",
        trends={
            "python": SkillTrend(
                skill_name="python",
                current_level="intermediate",
                previous_level="novice",
                direction=TrendDirection.STABLE,
                change_description="Stable level",
            )
        },
    )
    comp2, diff2 = engine._determine_complexity_and_difficulty(
        strategy=MentoringStrategy.PRACTICAL_EXERCISE,
        target_skill="python",
        profile=int_profile,
    )
    assert comp2 == "intermediate"
    assert diff2 == "intermediate"

    # 3. _build_tailored_guidance with empty steps
    _exp, steps = engine._build_tailored_guidance(
        strategy=MentoringStrategy.GUIDED_IMPLEMENTATION,
        complexity="targeted",
        query="test query",
        target_skill="rust",
        base_explanation="base explanation",
        base_steps=[],
    )
    assert len(steps) == 3
    assert "Review foundational principles for rust" in steps[0]
