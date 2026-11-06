"""Adaptive Mentoring Engine for PRISM IDE.

Extends the mentoring capabilities with dynamically calibrated strategies,
difficulty levels, explanation complexity, session effectiveness tracking,
and LLM + RAG intelligent synthesis with offline deterministic fallback.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from prism.intelligence.models.developer_intelligence_models import TrendDirection
from prism.llm.exceptions import LLMException
from prism.llm.schemas import LLMMessage, LLMRequest, LLMRole, StreamChunk
from prism.mentoring.engine import MentoringEngine
from prism.mentoring.models import (
    AdaptiveMentorRequest,
    AdaptiveMentorResponse,
    MentoringEffectiveness,
    MentoringSessionRecord,
    MentoringStrategy,
    MentorMode,
    MentorRequest,
)
from prism.storage.repositories.base import IntelligenceRepository

if TYPE_CHECKING:
    from prism.llm.context_builder import LLMContextBuilder
    from prism.llm.service import LLMService
    from prism.rag.service import RAGService

logger = logging.getLogger(__name__)


class AdaptiveMentoringEngine:
    """Adaptive mentoring engine personalizing pedagogical strategies to developer proficiency."""

    def __init__(
        self,
        intelligence_repo: IntelligenceRepository,
        base_mentor_engine: MentoringEngine | None = None,
        intelligence_engine: Any | None = None,
        task_engine: Any | None = None,
        llm_service: LLMService | None = None,
        context_builder: LLMContextBuilder | None = None,
        rag_service: RAGService | None = None,
    ) -> None:
        self.intelligence_repo = intelligence_repo
        self.base_mentor_engine = base_mentor_engine or MentoringEngine()
        self.intelligence_engine = intelligence_engine
        self.task_engine = task_engine
        self.llm_service = llm_service
        self.context_builder = context_builder
        self.rag_service = rag_service

    def request_adaptive_mentoring(
        self,
        request: AdaptiveMentorRequest,
    ) -> AdaptiveMentorResponse:
        """Process an adaptive mentoring request synchronously with optional LLM execution."""
        if self.llm_service is not None and request.use_llm:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                with ThreadPoolExecutor(max_workers=1) as executor:
                    return executor.submit(
                        asyncio.run, self.request_adaptive_mentoring_async(request)
                    ).result()
            return asyncio.run(self.request_adaptive_mentoring_async(request))

        return self._request_adaptive_mentoring_sync(request)

    async def request_adaptive_mentoring_async(
        self,
        request: AdaptiveMentorRequest,
    ) -> AdaptiveMentorResponse:
        """Process an adaptive mentoring request asynchronously with LLM and RAG integration."""
        if not request.developer_id.strip():
            raise ValueError("Developer ID cannot be empty")
        if not request.query.strip():
            raise ValueError("Query cannot be empty")

        now = datetime.now(UTC)
        session_id = f"ms_{uuid.uuid4().hex[:12]}"

        # Retrieve profile for personalization context
        profile = None
        if self.intelligence_engine and hasattr(
            self.intelligence_engine, "get_profile"
        ):
            try:
                profile = self.intelligence_engine.get_profile(request.developer_id)
            except (KeyError, ValueError, AttributeError, RuntimeError, OSError) as e:
                logger.warning("Could not fetch profile for adaptive mentoring: %s", e)

        # Select strategy
        strategy = request.preferred_strategy or self._select_strategy(
            query=request.query,
            target_skill=request.target_skill,
            profile=profile,
        )

        complexity, difficulty = self._determine_complexity_and_difficulty(
            strategy=strategy,
            target_skill=request.target_skill,
            profile=profile,
        )

        # Generate base mentor context and response
        base_req = MentorRequest(
            developer_id=request.developer_id,
            mode=MentorMode.LEARN,
            query=request.query,
            project_path=request.project_path,
            target_skill=request.target_skill,
            context_metadata=request.context_metadata,
        )
        base_res = self.base_mentor_engine.mentor(base_req)

        # Build fallback tailored explanations and actionable steps
        fallback_explanation, fallback_steps = self._build_tailored_guidance(
            strategy=strategy,
            complexity=complexity,
            query=request.query,
            target_skill=request.target_skill,
            base_explanation=base_res.explanation,
            base_steps=base_res.actionable_next_steps,
        )

        # Identify targeted knowledge gaps
        targeted_gaps: list[str] = []
        if profile and profile.active_gaps:
            if request.target_skill and request.target_skill in profile.active_gaps:
                targeted_gaps.append(request.target_skill)
            else:
                targeted_gaps.extend(profile.active_gaps[:2])
        elif request.target_skill:
            targeted_gaps.append(request.target_skill)

        # Recommend related tasks
        recommended_tasks: list[str] = []
        if self.task_engine and hasattr(self.task_engine, "generate_tasks"):
            try:
                tasks = self.task_engine.generate_tasks(
                    developer_id=request.developer_id,
                    target_role=request.context_metadata.get("target_role"),
                    limit=2,
                )
                recommended_tasks = [t.title for t in tasks]
            except (KeyError, ValueError, AttributeError, RuntimeError, OSError) as e:
                logger.warning(
                    "Could not generate recommended tasks for mentoring: %s", e
                )

        # RAG Context retrieval
        retrieved_citations: list[str] = []
        rag_context: str | None = None
        if self.rag_service and request.enable_rag:
            try:
                (
                    rag_context,
                    retrieved_chunks,
                ) = await self.rag_service.build_rag_context(
                    query=request.query, project_path=request.project_path, top_k=3
                )
                retrieved_citations = [rc.citation for rc in retrieved_chunks]
            except (KeyError, ValueError, AttributeError, RuntimeError, OSError) as e:
                logger.warning("RAG retrieval failed for mentoring: %s", e)

        # LLM Synthesis with offline fallback
        explanation = fallback_explanation
        actionable_steps = fallback_steps
        provider_used = "deterministic"

        if self.llm_service and request.use_llm:
            try:
                if self.context_builder:
                    messages = self.context_builder.assemble_mentoring_messages(
                        developer_id=request.developer_id,
                        query=request.query,
                        strategy=strategy,
                        explanation_complexity=complexity,
                        target_skill=request.target_skill,
                        project_context=request.project_path,
                        rag_context=rag_context,
                    )
                else:
                    sys_prompt = (
                        f"You are PRISM's expert AI mentor specializing in {strategy.value} "
                        f"at {complexity} level."
                    )
                    messages = [
                        LLMMessage(role=LLMRole.SYSTEM, content=sys_prompt),
                        LLMMessage(role=LLMRole.USER, content=request.query),
                    ]

                llm_req = LLMRequest(messages=messages, temperature=0.3)
                llm_res = await self.llm_service.generate(llm_req)
                explanation = llm_res.content
                provider_used = llm_res.provider

                parsed_steps = [
                    line.lstrip(" -*0123456789.)").strip()
                    for line in llm_res.content.splitlines()
                    if line.strip().startswith(("-", "*", "1.", "2.", "3.", "4.", "5."))
                ]
                if len(parsed_steps) >= 2:
                    actionable_steps = parsed_steps[:5]

            except (
                LLMException,
                KeyError,
                ValueError,
                AttributeError,
                RuntimeError,
                OSError,
            ) as e:
                logger.warning(
                    "LLM mentoring generation failed, falling back to deterministic: %s",
                    e,
                )
                explanation = fallback_explanation
                actionable_steps = fallback_steps
                provider_used = "deterministic_fallback"

        summary = (
            f"Adaptive Mentoring ({strategy.value.replace('_', ' ').title()}) "
            f"tailored to {complexity} level for '{request.query[:60]}'."
        )

        response = AdaptiveMentorResponse(
            session_id=session_id,
            developer_id=request.developer_id,
            selected_strategy=strategy,
            explanation_complexity=complexity,
            mentoring_difficulty=difficulty,
            summary=summary,
            explanation=explanation,
            actionable_steps=actionable_steps,
            targeted_knowledge_gaps=targeted_gaps,
            recommended_tasks=recommended_tasks,
            retrieved_citations=retrieved_citations,
            provider_used=provider_used,
            created_at=now,
        )

        # Record mentoring session
        session_record = MentoringSessionRecord(
            session_id=session_id,
            developer_id=request.developer_id,
            strategy=strategy,
            query=request.query,
            target_skill=request.target_skill,
            summary=summary,
            provider_used=provider_used,
            metadata_json={"retrieved_citations": retrieved_citations},
            created_at=now,
        )

        try:
            self.intelligence_repo.save_mentoring_session(session_record)
        except (KeyError, ValueError, AttributeError, RuntimeError, OSError) as e:
            logger.warning(
                "Failed to persist mentoring session record %s: %s", session_id, e
            )

        return response

    async def request_adaptive_mentoring_stream(
        self,
        request: AdaptiveMentorRequest,
    ) -> AsyncIterator[StreamChunk]:
        """Stream adaptive mentoring tokens directly via LLM or simulated streaming."""
        if not request.developer_id.strip():
            raise ValueError("Developer ID cannot be empty")
        if not request.query.strip():
            raise ValueError("Query cannot be empty")

        profile = None
        if self.intelligence_engine and hasattr(
            self.intelligence_engine, "get_profile"
        ):
            try:
                profile = self.intelligence_engine.get_profile(request.developer_id)
            except (KeyError, ValueError, AttributeError, RuntimeError, OSError) as e:
                logger.warning("Could not fetch profile for adaptive stream: %s", e)

        strategy = request.preferred_strategy or self._select_strategy(
            query=request.query,
            target_skill=request.target_skill,
            profile=profile,
        )
        complexity, _ = self._determine_complexity_and_difficulty(
            strategy=strategy,
            target_skill=request.target_skill,
            profile=profile,
        )

        rag_context = None
        if self.rag_service and request.enable_rag:
            try:
                rag_context, _ = await self.rag_service.build_rag_context(
                    query=request.query, project_path=request.project_path, top_k=3
                )
            except (KeyError, ValueError, AttributeError, RuntimeError, OSError) as e:
                logger.warning("RAG retrieval failed during stream setup: %s", e)

        if self.llm_service and request.use_llm:
            try:
                if self.context_builder:
                    messages = self.context_builder.assemble_mentoring_messages(
                        developer_id=request.developer_id,
                        query=request.query,
                        strategy=strategy,
                        explanation_complexity=complexity,
                        target_skill=request.target_skill,
                        project_context=request.project_path,
                        rag_context=rag_context,
                    )
                else:
                    messages = [
                        LLMMessage(
                            role=LLMRole.SYSTEM,
                            content=f"You are PRISM's expert AI mentor specializing in {strategy.value}.",
                        ),
                        LLMMessage(role=LLMRole.USER, content=request.query),
                    ]
                llm_req = LLMRequest(messages=messages, temperature=0.3)
                async for chunk in self.llm_service.generate_stream(llm_req):
                    yield chunk
                return
            except (
                LLMException,
                KeyError,
                ValueError,
                AttributeError,
                RuntimeError,
                OSError,
            ) as e:
                logger.warning(
                    "Streaming failed from LLM, falling back to simulated stream: %s", e
                )

        # Fallback simulated stream
        base_req = MentorRequest(
            developer_id=request.developer_id,
            mode=MentorMode.LEARN,
            query=request.query,
            project_path=request.project_path,
            target_skill=request.target_skill,
            context_metadata=request.context_metadata,
        )
        base_res = self.base_mentor_engine.mentor(base_req)
        fallback_explanation, _ = self._build_tailored_guidance(
            strategy=strategy,
            complexity=complexity,
            query=request.query,
            target_skill=request.target_skill,
            base_explanation=base_res.explanation,
            base_steps=base_res.actionable_next_steps,
        )

        words = fallback_explanation.split(" ")
        for i, word in enumerate(words):
            token = word + (" " if i < len(words) - 1 else "")
            is_last = i == len(words) - 1
            yield StreamChunk(
                delta=token,
                finish_reason="stop" if is_last else None,
                provider="deterministic",
            )

    def _request_adaptive_mentoring_sync(
        self,
        request: AdaptiveMentorRequest,
    ) -> AdaptiveMentorResponse:
        """Process an adaptive mentoring request tailored to developer level synchronously."""
        if not request.developer_id.strip():
            raise ValueError("Developer ID cannot be empty")
        if not request.query.strip():
            raise ValueError("Query cannot be empty")

        now = datetime.now(UTC)
        session_id = f"ms_{uuid.uuid4().hex[:12]}"

        # Retrieve profile for personalization context
        profile = None
        if self.intelligence_engine and hasattr(
            self.intelligence_engine, "get_profile"
        ):
            try:
                profile = self.intelligence_engine.get_profile(request.developer_id)
            except (KeyError, ValueError, AttributeError, RuntimeError, OSError) as e:
                logger.warning("Could not fetch profile for adaptive mentoring: %s", e)

        # Select strategy
        strategy = request.preferred_strategy or self._select_strategy(
            query=request.query,
            target_skill=request.target_skill,
            profile=profile,
        )

        complexity, difficulty = self._determine_complexity_and_difficulty(
            strategy=strategy,
            target_skill=request.target_skill,
            profile=profile,
        )

        # Generate base mentor context and response
        base_req = MentorRequest(
            developer_id=request.developer_id,
            mode=MentorMode.LEARN,
            query=request.query,
            project_path=request.project_path,
            target_skill=request.target_skill,
            context_metadata=request.context_metadata,
        )
        base_res = self.base_mentor_engine.mentor(base_req)

        # Build tailored explanations and actionable steps
        explanation, actionable_steps = self._build_tailored_guidance(
            strategy=strategy,
            complexity=complexity,
            query=request.query,
            target_skill=request.target_skill,
            base_explanation=base_res.explanation,
            base_steps=base_res.actionable_next_steps,
        )

        # Identify targeted knowledge gaps
        targeted_gaps: list[str] = []
        if profile and profile.active_gaps:
            if request.target_skill and request.target_skill in profile.active_gaps:
                targeted_gaps.append(request.target_skill)
            else:
                targeted_gaps.extend(profile.active_gaps[:2])
        elif request.target_skill:
            targeted_gaps.append(request.target_skill)

        # Recommend related tasks
        recommended_tasks: list[str] = []
        if self.task_engine and hasattr(self.task_engine, "generate_tasks"):
            try:
                tasks = self.task_engine.generate_tasks(
                    developer_id=request.developer_id,
                    target_role=request.context_metadata.get("target_role"),
                    limit=2,
                )
                recommended_tasks = [t.title for t in tasks]
            except (KeyError, ValueError, AttributeError, RuntimeError, OSError) as e:
                logger.warning(
                    "Could not generate recommended tasks for mentoring: %s", e
                )

        summary = (
            f"Adaptive Mentoring ({strategy.value.replace('_', ' ').title()}) "
            f"tailored to {complexity} level for '{request.query[:60]}'."
        )

        response = AdaptiveMentorResponse(
            session_id=session_id,
            developer_id=request.developer_id,
            selected_strategy=strategy,
            explanation_complexity=complexity,
            mentoring_difficulty=difficulty,
            summary=summary,
            explanation=explanation,
            actionable_steps=actionable_steps,
            targeted_knowledge_gaps=targeted_gaps,
            recommended_tasks=recommended_tasks,
            retrieved_citations=[],
            provider_used="deterministic",
            created_at=now,
        )

        # Record mentoring session
        session_record = MentoringSessionRecord(
            session_id=session_id,
            developer_id=request.developer_id,
            strategy=strategy,
            query=request.query,
            target_skill=request.target_skill,
            summary=summary,
            provider_used="deterministic",
            metadata_json={},
            created_at=now,
        )

        try:
            self.intelligence_repo.save_mentoring_session(session_record)
        except (KeyError, ValueError, AttributeError, RuntimeError, OSError) as e:
            logger.warning(
                "Failed to persist mentoring session record %s: %s", session_id, e
            )

        return response

    def _select_strategy(
        self,
        query: str,
        target_skill: str | None,
        profile: Any | None,
    ) -> MentoringStrategy:
        """Select appropriate strategy based on keywords and proficiency."""
        q_lower = query.lower()
        if any(
            w in q_lower for w in ("error", "bug", "fail", "broken", "traceback", "fix")
        ):
            return MentoringStrategy.DEBUGGING_GUIDANCE
        if any(
            w in q_lower
            for w in ("exercise", "practice", "hands-on", "build", "project")
        ):
            return MentoringStrategy.PRACTICAL_EXERCISE
        if any(
            w in q_lower
            for w in ("architecture", "scale", "optimize", "advanced", "concurrency")
        ):
            return MentoringStrategy.ADVANCED_TECHNICAL_GUIDANCE

        # Check target skill proficiency in profile trends
        if profile and target_skill and target_skill in profile.trends:
            trend = profile.trends[target_skill]
            if trend.current_level in ("elementary", "novice"):
                return MentoringStrategy.CONCEPTUAL_EXPLANATION
            if trend.current_level in ("proficient", "advanced"):
                return MentoringStrategy.ADVANCED_TECHNICAL_GUIDANCE

        if profile and target_skill and target_skill in profile.active_gaps:
            return MentoringStrategy.STEP_BY_STEP_LEARNING

        return MentoringStrategy.GUIDED_IMPLEMENTATION

    def _determine_complexity_and_difficulty(
        self,
        strategy: MentoringStrategy,
        target_skill: str | None,
        profile: Any | None,
    ) -> tuple[str, str]:
        """Determine complexity and difficulty labels."""
        if strategy == MentoringStrategy.ADVANCED_TECHNICAL_GUIDANCE:
            return "advanced", "advanced"
        if strategy in (
            MentoringStrategy.CONCEPTUAL_EXPLANATION,
            MentoringStrategy.STEP_BY_STEP_LEARNING,
        ):
            return "foundational", "beginner"
        if strategy == MentoringStrategy.DEBUGGING_GUIDANCE:
            return "targeted", "intermediate"

        if profile and target_skill and target_skill in profile.trends:
            lvl = profile.trends[target_skill].current_level
            if lvl in ("proficient", "advanced"):
                return "advanced", "advanced"
            if lvl in ("intermediate",):
                return "intermediate", "intermediate"

        return "intermediate", "intermediate"

    def _build_tailored_guidance(
        self,
        strategy: MentoringStrategy,
        complexity: str,
        query: str,
        target_skill: str | None,
        base_explanation: str,
        base_steps: list[str],
    ) -> tuple[str, list[str]]:
        """Construct detailed pedagogical explanation and actionable steps."""
        strategy_headers = {
            MentoringStrategy.CONCEPTUAL_EXPLANATION: (
                "Foundational Core Concepts:\n"
                "Let's break down the fundamental mental models before diving into code."
            ),
            MentoringStrategy.GUIDED_IMPLEMENTATION: (
                "Guided Implementation Walkthrough:\n"
                "Follow this blueprint to implement the solution with idiomatic design patterns."
            ),
            MentoringStrategy.STEP_BY_STEP_LEARNING: (
                "Structured Step-by-Step Learning:\n"
                "Take each phase sequentially, validating outcomes at every stage."
            ),
            MentoringStrategy.DEBUGGING_GUIDANCE: (
                "Diagnostic & Debugging Protocol:\n"
                "Isolate the root cause using methodical verification and structured checks."
            ),
            MentoringStrategy.PRACTICAL_EXERCISE: (
                "Applied Hands-on Practice:\n"
                "Solidify your understanding by constructing this concrete deliverable."
            ),
            MentoringStrategy.ADVANCED_TECHNICAL_GUIDANCE: (
                "Advanced Architectural & Performance Insights:\n"
                "Examine concurrency, resource lifecycle, and edge-case resilience."
            ),
        }

        header = strategy_headers.get(
            strategy,
            "Targeted Architectural Recommendation:",
        )
        skill_ref = f" relating to {target_skill}" if target_skill else ""
        explanation = f"{header}\n\nAddressing '{query}'{skill_ref} at {complexity} level:\n\n{base_explanation}"

        steps = list(base_steps)
        if not steps:
            steps = [
                f"Review foundational principles for {target_skill or 'this domain'}.",
                "Write an isolated test case reproducing the required behavior.",
                "Execute the implementation and verify all tests pass.",
            ]

        return explanation, steps

    def get_session_history(
        self,
        developer_id: str,
        limit: int = 20,
    ) -> list[MentoringSessionRecord]:
        """Fetch historical mentoring sessions for a developer."""
        return self.intelligence_repo.get_mentoring_sessions(developer_id, limit=limit)

    def get_mentoring_effectiveness(
        self,
        developer_id: str,
    ) -> MentoringEffectiveness:
        """Calculate mentoring effectiveness scores and distribution for a developer."""
        sessions = self.intelligence_repo.get_mentoring_sessions(
            developer_id, limit=100
        )
        total_sessions = len(sessions)
        if total_sessions == 0:
            return MentoringEffectiveness(developer_id=developer_id)

        ratings = [s.outcome_rating for s in sessions if s.outcome_rating is not None]
        avg_rating = sum(ratings) / len(ratings) if ratings else 4.0

        dist: dict[str, int] = {}
        for s in sessions:
            strat_val = s.strategy.value
            dist[strat_val] = dist.get(strat_val, 0) + 1

        # Calculate correlated improvements from profile trends
        improved_trends = 0
        if self.intelligence_engine and hasattr(
            self.intelligence_engine, "get_profile"
        ):
            try:
                prof = self.intelligence_engine.get_profile(developer_id)
                for t in prof.trends.values():
                    if t.direction == TrendDirection.IMPROVING:
                        improved_trends += 1
            except (KeyError, ValueError, AttributeError, RuntimeError, OSError) as e:
                logger.warning("Could not assess trends for effectiveness: %s", e)

        # Score computation bounded between 0.0 and 1.0
        normalized_rating = min(1.0, max(0.0, avg_rating / 5.0))
        volume_weight = min(1.0, total_sessions / 10.0)
        effectiveness_score = round(normalized_rating * 0.7 + volume_weight * 0.3, 2)

        return MentoringEffectiveness(
            developer_id=developer_id,
            total_sessions=total_sessions,
            average_rating=round(avg_rating, 2),
            strategy_distribution=dist,
            skill_improvements_correlated=improved_trends,
            effectiveness_score=effectiveness_score,
        )
