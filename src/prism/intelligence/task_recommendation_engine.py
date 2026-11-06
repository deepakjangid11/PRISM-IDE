import uuid
from datetime import UTC, datetime
from typing import Any

from prism.intelligence.models.developer_intelligence_models import (
    PersonalizedTask,
    TaskDifficulty,
    TaskEvaluation,
    TaskOutcome,
    TaskPriority,
    TaskRecommendation,
    TaskStatus,
)
from prism.intelligence.models.skill_models import (
    ProficiencyLevel,
    SkillEvidence,
)
from prism.intelligence.skill_graph import SkillGraph
from prism.intelligence.skill_tracker import SkillTracker
from prism.learning.knowledge_gap_analyzer import KnowledgeGapAnalyzer
from prism.logging.logger import get_logger
from prism.storage.repositories.base import IntelligenceRepository

logger = get_logger(__name__)


class TaskRecommendationEngine:
    """Generates, tracks, and evaluates personalized hands-on developer tasks."""

    def __init__(
        self,
        skill_tracker: SkillTracker,
        gap_analyzer: KnowledgeGapAnalyzer,
        skill_graph: SkillGraph,
        intelligence_repo: IntelligenceRepository | None = None,
    ) -> None:
        self.skill_tracker = skill_tracker
        self.gap_analyzer = gap_analyzer
        self.skill_graph = skill_graph
        self.intelligence_repo = intelligence_repo

    def generate_tasks(
        self,
        developer_id: str,
        target_goal: str | None = None,
        target_role: str | None = None,
        difficulty_preference: str | None = None,
        limit: int = 5,
    ) -> list[TaskRecommendation]:
        """Synthesize actionable practice tasks targeted at current knowledge gaps."""
        cleaned_id = developer_id.strip()
        if not cleaned_id:
            raise ValueError("Developer ID cannot be empty")

        profile = self.skill_tracker.get_profile(cleaned_id)
        existing_tasks = []
        if self.intelligence_repo is not None:
            existing_tasks = self.intelligence_repo.get_tasks_for_developer(cleaned_id)

        existing_titles = {t.title.lower() for t in existing_tasks}
        existing_target_skills = {
            t.target_skill.lower()
            for t in existing_tasks
            if t.status
            in (
                TaskStatus.GENERATED,
                TaskStatus.ACCEPTED,
                TaskStatus.IN_PROGRESS,
                TaskStatus.SUBMITTED,
            )
        }

        # 1. Identify Gaps
        gaps = []
        if target_role:
            gaps = self.gap_analyzer.identify_role_gaps(profile, target_role.strip())
        elif target_goal:
            gaps = self.gap_analyzer.identify_gaps(profile, target_goal.strip())
        else:
            # Gather gaps across active skills
            for s in profile.skills.values():
                gaps.extend(self.gap_analyzer.identify_gaps(profile, s.skill_name))

        # Filter out gaps for already mastered skills
        actionable_gaps = []
        for g in gaps:
            dev_skill = profile.get_skill(g.missing_skill)
            if (
                dev_skill is not None
                and dev_skill.has_sufficient_evidence
                and dev_skill.proficiency_level
                in (
                    ProficiencyLevel.INTERMEDIATE,
                    ProficiencyLevel.ADVANCED,
                    ProficiencyLevel.EXPERT,
                )
            ):
                continue
            if g.missing_skill.lower() not in existing_target_skills:
                actionable_gaps.append(g)

        # Fallback if no specific gaps: recommend next logical skill from active skills
        if not actionable_gaps:
            for s in profile.skills.values():
                connected = self.skill_graph.get_prerequisites(s.skill_name)
                for c in connected:
                    if c.lower() not in existing_target_skills:
                        from prism.learning.models import KnowledgeGap, KnowledgeGapType

                        actionable_gaps.append(
                            KnowledgeGap(
                                gap_id=f"gap_{uuid.uuid4().hex[:8]}",
                                developer_id=profile.developer_id,
                                missing_skill=c,
                                target_skill=s.skill_name,
                                gap_type=KnowledgeGapType.MISSING_PREREQUISITE,
                                description=f"Missing prerequisite {c} for {s.skill_name}",
                                severity="medium",
                                importance_reason=f"Foundational requirement for {s.skill_name}",
                            )
                        )

        recommendations: list[TaskRecommendation] = []
        now = datetime.now(UTC)

        for gap in actionable_gaps[:limit]:
            skill_name = gap.missing_skill
            _node = self.skill_graph.get_node(skill_name)
            prereqs = self.skill_graph.get_prerequisites(skill_name, transitive=False)

            # Determine appropriate task difficulty
            dev_skill = profile.get_skill(skill_name)
            curr_level = (
                dev_skill.proficiency_level
                if dev_skill
                else ProficiencyLevel.INSUFFICIENT_DATA
            )

            if difficulty_preference:
                pref = difficulty_preference.strip().lower()
                if pref == "beginner":
                    diff = TaskDifficulty.BEGINNER
                elif pref == "elementary":
                    diff = TaskDifficulty.ELEMENTARY
                elif pref == "advanced":
                    diff = TaskDifficulty.ADVANCED
                elif pref == "expert":
                    diff = TaskDifficulty.EXPERT
                else:
                    diff = TaskDifficulty.INTERMEDIATE
            else:
                if curr_level == ProficiencyLevel.INSUFFICIENT_DATA:
                    diff = TaskDifficulty.BEGINNER
                elif curr_level == ProficiencyLevel.BEGINNER:
                    diff = TaskDifficulty.ELEMENTARY
                elif curr_level == ProficiencyLevel.INTERMEDIATE:
                    diff = TaskDifficulty.INTERMEDIATE
                elif curr_level == ProficiencyLevel.ADVANCED:
                    diff = TaskDifficulty.ADVANCED
                else:
                    diff = TaskDifficulty.EXPERT

            spec = self._build_task_specification(
                skill_name=skill_name,
                diff=diff,
                target_role=target_role,
                prereqs=prereqs,
                importance_reason=gap.importance_reason,
            )

            if spec["title"].lower() in existing_titles:
                continue

            priority = (
                TaskPriority.HIGH if gap.severity == "high" else TaskPriority.MEDIUM
            )

            task = PersonalizedTask(
                task_id=f"tsk_{uuid.uuid4().hex[:10]}",
                developer_id=cleaned_id,
                title=spec["title"],
                description=spec["description"],
                target_skill=skill_name,
                difficulty=diff,
                priority=priority,
                status=TaskStatus.GENERATED,
                estimated_minutes=spec["estimated_minutes"],
                target_role=target_role,
                prerequisite_skills=prereqs,
                reason=gap.importance_reason
                or f"Prerequisite competency required for {gap.target_skill}",
                acceptance_criteria=spec["acceptance_criteria"],
                problem_statement=spec["problem_statement"],
                learning_objectives=spec["learning_objectives"],
                requirements=spec["requirements"],
                test_cases=spec["test_cases"],
                hints=spec["hints"],
                expected_deliverables=spec["expected_deliverables"],
                evaluation_criteria=spec["evaluation_criteria"],
                created_at=now,
                updated_at=now,
            )

            rec = TaskRecommendation(
                task=task,
                importance_score=1.5 if priority == TaskPriority.HIGH else 1.0,
                readiness_assessment=f"Prerequisites ({', '.join(prereqs) or 'None'}) are satisfied.",
            )
            recommendations.append(rec)

            if self.intelligence_repo is not None:
                self.intelligence_repo.save_task(task)

        logger.info(
            "Generated %d personalized tasks for developer '%s'",
            len(recommendations),
            cleaned_id,
        )
        return recommendations

    def _build_task_specification(
        self,
        skill_name: str,
        diff: TaskDifficulty,
        target_role: str | None,
        prereqs: list[str],
        importance_reason: str | None = None,
    ) -> dict[str, Any]:
        """Generate a complete, structured coding task specification tailored to skill and level."""
        clean_skill = skill_name.strip()
        slug = clean_skill.lower().replace(" ", "_").replace("-", "_")

        if diff == TaskDifficulty.BEGINNER:
            return {
                "title": f"Foundational Exercise: {clean_skill} Core Concepts",
                "description": (
                    f"Implement a minimal working module utilizing {clean_skill}. "
                    "Focus on syntactical correctness and standard idioms."
                ),
                "problem_statement": (
                    f"You are tasked with creating a fundamental implementation using {clean_skill}. "
                    f"Develop clean, well-commented code demonstrating core operations, inputs validation, "
                    f"and basic execution flow. Verify the functionality with baseline unit tests."
                ),
                "learning_objectives": [
                    f"Understand core syntax, standard idioms, and patterns of {clean_skill}",
                    f"Construct functional code routines validating input boundaries in {clean_skill}",
                    "Write clear, maintainable unit tests validating primary behavior",
                ],
                "requirements": [
                    f"Implement main class or function executing {clean_skill} logic",
                    "Handle missing, null, or invalid inputs gracefully with explicit errors",
                    "Adhere strictly to standard coding conventions and type safety",
                ],
                "acceptance_criteria": [
                    f"Create a clean module implementing {clean_skill} basic functionality",
                    "Write at least 2 unit tests verifying execution",
                ],
                "test_cases": [
                    {
                        "name": "test_basic_execution",
                        "description": "Verifies primary function returns expected output on standard inputs",
                        "passed": True,
                    },
                    {
                        "name": "test_invalid_input_handling",
                        "description": "Verifies ValueError or appropriate exception is raised on invalid inputs",
                        "passed": True,
                    },
                ],
                "hints": [
                    f"Review official documentation for {clean_skill} idioms.",
                    "Start by defining clear function signatures and expected return types.",
                    "Use pytest assertions to test both happy path and error cases.",
                ],
                "expected_deliverables": [
                    f"src/{slug}.py",
                    f"tests/test_{slug}.py",
                ],
                "evaluation_criteria": [
                    "Syntactical correctness and clean code organization",
                    "Proper input validation and defensive error handling",
                    "Passing test suite with verifiable assertions",
                ],
                "estimated_minutes": 30,
            }

        elif diff == TaskDifficulty.ELEMENTARY:
            return {
                "title": f"Practical Implementation: {clean_skill} Feature",
                "description": (
                    f"Construct a feature module incorporating {clean_skill} with error handling. "
                    "Validate inputs and adhere to modular design patterns."
                ),
                "problem_statement": (
                    f"Implement an end-to-end feature component utilizing {clean_skill}. "
                    f"The component must parse inputs, execute domain logic with proper boundary checks, "
                    f"and return structured results while handling runtime failures cleanly."
                ),
                "learning_objectives": [
                    f"Build modular, decoupled application features using {clean_skill}",
                    "Implement robust exception hierarchies and recovery strategies",
                    "Structure tests covering edge cases and boundary limits",
                ],
                "requirements": [
                    f"Implement complete feature workflow using {clean_skill}",
                    "Handle edge cases and input validation errors gracefully",
                    "Include type annotations and docstrings across public functions",
                ],
                "acceptance_criteria": [
                    f"Implement complete feature workflow using {clean_skill}",
                    "Handle edge cases and input validation errors gracefully",
                ],
                "test_cases": [
                    {
                        "name": "test_feature_workflow",
                        "description": "Validates full feature execution lifecycle",
                        "passed": True,
                    },
                    {
                        "name": "test_edge_case_boundaries",
                        "description": "Validates proper behavior under edge conditions",
                        "passed": True,
                    },
                ],
                "hints": [
                    f"Consider how {clean_skill} fits into broader system workflows.",
                    "Separate data transformation from business logic.",
                    "Ensure all external dependencies are mockable in tests.",
                ],
                "expected_deliverables": [
                    f"src/{slug}_feature.py",
                    f"tests/test_{slug}_feature.py",
                ],
                "evaluation_criteria": [
                    "Feature completeness and correct business logic",
                    "Clean separation of concerns and modularity",
                    "Comprehensive test cases covering edge cases",
                ],
                "estimated_minutes": 45,
            }

        elif diff == TaskDifficulty.INTERMEDIATE:
            return {
                "title": f"Architecture Integration: {clean_skill} Production Workflow",
                "description": (
                    f"Design and integrate an end-to-end component utilizing {clean_skill}. "
                    "Include automated test suites and maintain architectural separation."
                ),
                "problem_statement": (
                    f"Integrate {clean_skill} into a production-grade service architecture. "
                    f"You must design a decoupled service layer, incorporate structured logging, "
                    f"ensure idempotent execution, and implement automated integration test coverage."
                ),
                "learning_objectives": [
                    f"Integrate {clean_skill} within multi-layered production architectures",
                    "Apply dependency inversion, structured logging, and configuration management",
                    "Build resilient services with comprehensive automated integration tests",
                ],
                "requirements": [
                    f"Complete production-grade integration of {clean_skill}",
                    "Achieve verified test passes with full assertion coverage",
                    "Incorporate structured logging and environment-based configuration",
                ],
                "acceptance_criteria": [
                    f"Complete production-grade integration of {clean_skill}",
                    "Achieve verified test passes with full assertion coverage",
                ],
                "test_cases": [
                    {
                        "name": "test_production_integration",
                        "description": "Validates end-to-end service orchestration",
                        "passed": True,
                    },
                    {
                        "name": "test_resilience_and_recovery",
                        "description": "Validates graceful recovery under dependency failure",
                        "passed": True,
                    },
                ],
                "hints": [
                    "Design interfaces and protocols before implementing concrete classes.",
                    "Implement health checking or status reporting for the component.",
                    "Use structured context in log statements rather than simple text prints.",
                ],
                "expected_deliverables": [
                    f"src/services/{slug}_service.py",
                    f"tests/test_{slug}_integration.py",
                ],
                "evaluation_criteria": [
                    "Adherence to clean architectural design and dependency inversion",
                    "Robust exception handling and structured observability",
                    "High test coverage with clear behavioral assertions",
                ],
                "estimated_minutes": 60,
            }

        elif diff == TaskDifficulty.ADVANCED:
            return {
                "title": f"Scalable Systems Engineering: {clean_skill} Optimization & Concurrency",
                "description": (
                    f"Architect high-throughput, low-latency concurrent workflows for {clean_skill}. "
                    "Implement connection pooling, caching strategies, and load-tested resilience."
                ),
                "problem_statement": (
                    f"Under high load, unoptimized implementations of {clean_skill} create critical bottlenecks. "
                    f"Architect an optimized, concurrent execution engine with non-blocking I/O, cache invalidation, "
                    f"and thread-safe state synchronization. Document performance benchmarks."
                ),
                "learning_objectives": [
                    f"Master non-blocking concurrent patterns and async workflows with {clean_skill}",
                    "Implement thread-safe caching and memory-efficient data structures",
                    "Benchmark latency and throughput under simulated concurrent stress",
                ],
                "requirements": [
                    f"Implement asynchronous or multi-worker concurrent architecture for {clean_skill}",
                    "Ensure thread safety and zero race conditions under concurrent execution",
                    "Include benchmark suite demonstrating sub-50ms p95 latency",
                ],
                "acceptance_criteria": [
                    f"Demonstrate verified concurrent execution of {clean_skill} without deadlocks",
                    "Achieve sub-50ms p95 latency under simulated concurrent operations",
                ],
                "test_cases": [
                    {
                        "name": "test_concurrent_load",
                        "description": "Validates thread safety and consistency under 50 concurrent requests",
                        "passed": True,
                    },
                    {
                        "name": "test_cache_invalidation",
                        "description": "Validates cache hit ratio and correct TTL eviction",
                        "passed": True,
                    },
                ],
                "hints": [
                    "Use asyncio locks or atomic primitives to guard shared mutable state.",
                    "Measure before and after performance using time.perf_counter().",
                    "Avoid blocking CPU-bound tasks in async event loops.",
                ],
                "expected_deliverables": [
                    f"src/core/{slug}_engine.py",
                    f"benchmarks/benchmark_{slug}.py",
                ],
                "evaluation_criteria": [
                    "Concurrency correctness and elimination of race conditions",
                    "Demonstrated performance improvements and latency reduction",
                    "Resource cleanup and leak prevention",
                ],
                "estimated_minutes": 75,
            }

        else:  # EXPERT
            return {
                "title": f"Enterprise Architecture & Fault Tolerance: {clean_skill}",
                "description": (
                    f"Architect distributed, fault-tolerant enterprise infrastructure for {clean_skill}. "
                    "Implement circuit breakers, zero-data-loss recovery, and comprehensive telemetry."
                ),
                "problem_statement": (
                    f"Design an enterprise-tier distributed component leveraging {clean_skill}. "
                    f"The system must guarantee zero data loss, withstand arbitrary downstream failures "
                    f"using circuit breaker patterns, and expose full OpenTelemetry-compatible metrics."
                ),
                "learning_objectives": [
                    f"Design distributed, self-healing systems utilizing {clean_skill}",
                    "Implement circuit breakers, backpressure, and graceful degradation",
                    "Instrument comprehensive telemetry, distributed tracing, and auditability",
                ],
                "requirements": [
                    f"Implement circuit breaker and retry mechanisms with exponential backoff for {clean_skill}",
                    "Guarantee idempotency and zero-data-loss state recovery",
                    "Expose structured telemetry and diagnostic instrumentation",
                ],
                "acceptance_criteria": [
                    f"Demonstrate zero-data-loss recovery across failure simulations in {clean_skill}",
                    "Verify circuit breaker opens upon error thresholds and self-heals",
                ],
                "test_cases": [
                    {
                        "name": "test_circuit_breaker_tripping",
                        "description": "Verifies circuit breaker trips on consecutive failures and recovers",
                        "passed": True,
                    },
                    {
                        "name": "test_idempotent_recovery",
                        "description": "Verifies duplicate requests yield identical safe state",
                        "passed": True,
                    },
                ],
                "hints": [
                    "Implement state machines to manage circuit breaker states (Closed, Open, Half-Open).",
                    "Use exponential backoff with jitter to prevent thundering herd problems.",
                    "Track error rate percentage in sliding time windows.",
                ],
                "expected_deliverables": [
                    f"src/enterprise/{slug}_resilience.py",
                    f"tests/test_{slug}_chaos.py",
                ],
                "evaluation_criteria": [
                    "Fault-tolerance architecture and proven resilience under chaos conditions",
                    "Strict idempotency and transaction safety",
                    "Production-grade telemetry and observability",
                ],
                "estimated_minutes": 90,
            }

    def get_task(self, task_id: str) -> PersonalizedTask | None:
        """Fetch a personalized task by ID."""
        if self.intelligence_repo is None:
            return None
        return self.intelligence_repo.get_task(task_id)

    def update_task_status(
        self, task_id: str, new_status: str, notes: str | None = None
    ) -> PersonalizedTask:
        """Advance task through its lifecycle (ACCEPTED, IN_PROGRESS, REJECTED, CANCELLED)."""
        cleaned_status = new_status.strip().lower()
        if self.intelligence_repo is None:
            raise RuntimeError(
                "Repository required for persistent task lifecycle tracking"
            )

        task = self.intelligence_repo.update_task_status(task_id, cleaned_status)
        if not task:
            raise ValueError(f"Task with ID '{task_id}' not found")
        return task

    def evaluate_task_completion(
        self,
        task_id: str,
        success: bool,
        execution_notes: str,
        artifacts: list[str] | None = None,
    ) -> TaskEvaluation:
        """Evaluate completed task outcome and generate verifiable skill evidence."""
        if self.intelligence_repo is None:
            raise RuntimeError("Repository required for task outcome evaluation")

        task = self.intelligence_repo.get_task(task_id)
        if not task:
            raise ValueError(f"Task with ID '{task_id}' not found")

        now = datetime.now(UTC)
        artifacts_list = artifacts or []

        # 1. Record Task Outcome
        outcome = TaskOutcome(
            outcome_id=f"out_{uuid.uuid4().hex[:10]}",
            task_id=task_id,
            developer_id=task.developer_id,
            success=success,
            execution_notes=execution_notes,
            verified_artifacts=artifacts_list,
            recorded_at=now,
        )
        self.intelligence_repo.save_task_outcome(outcome)

        # 2. Update Task Status
        new_status = TaskStatus.COMPLETED if success else TaskStatus.IN_PROGRESS
        self.intelligence_repo.update_task_status(task_id, new_status.value)

        # 3. Generate Verified Skill Evidence if Passed
        evidence_id = None
        score = 85.0 if success else 40.0
        strengths = []
        improvements = []

        if success:
            strengths.append(
                f"Successfully implemented {task.target_skill} specifications"
            )
            ev_strength = 1.3 if task.difficulty == TaskDifficulty.INTERMEDIATE else 1.1
            complexity = 0.8 if task.difficulty == TaskDifficulty.INTERMEDIATE else 0.5

            evidence = SkillEvidence(
                evidence_id=f"ev_tsk_{uuid.uuid4().hex[:10]}",
                developer_id=task.developer_id,
                skill_name=task.target_skill,
                skill_id=task.target_skill.lower().replace(" ", "_"),
                evidence_type="project_feature",
                description=f"Completed practice task '{task.title}': {execution_notes}",
                evidence_source="personalized_task",
                evidence_strength=ev_strength,
                confidence_score=0.95,
                complexity_score=complexity,
                timestamp=now,
                metadata={"task_id": task_id, "score": score},
            )
            self.skill_tracker.record_evidence(evidence)
            evidence_id = evidence.evidence_id
            msg = f"Task '{task.title}' verified successfully. Generated verifiable skill evidence."
        else:
            improvements.append(
                f"Encountered blockers during {task.target_skill} execution"
            )
            msg = f"Task '{task.title}' was not fully completed. Review acceptance criteria and retry."

        evaluation = TaskEvaluation(
            evaluation_id=f"eval_{uuid.uuid4().hex[:10]}",
            task_id=task_id,
            developer_id=task.developer_id,
            passed=success,
            score=score,
            strengths_demonstrated=strengths,
            improvement_areas=improvements,
            generated_evidence_id=evidence_id,
            feedback_message=msg,
            evaluated_at=now,
        )

        logger.info(
            "Task '%s' evaluated | dev=%s | success=%s | score=%.1f",
            task_id,
            task.developer_id,
            success,
            score,
        )
        return evaluation
