import uuid
from datetime import UTC, datetime

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
            in (TaskStatus.GENERATED, TaskStatus.ACCEPTED, TaskStatus.IN_PROGRESS)
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

            if curr_level == ProficiencyLevel.INSUFFICIENT_DATA:
                diff = TaskDifficulty.BEGINNER
                title = f"Foundational Exercise: {skill_name} Core Concepts"
                desc = (
                    f"Implement a minimal working module utilizing {skill_name}. "
                    "Focus on syntactical correctness and standard idioms."
                )
                criteria = [
                    f"Create a clean module implementing {skill_name} basic functionality",
                    "Write at least 2 unit tests verifying execution",
                ]
            elif curr_level == ProficiencyLevel.BEGINNER:
                diff = TaskDifficulty.ELEMENTARY
                title = f"Practical Implementation: {skill_name} Feature"
                desc = (
                    f"Construct a feature module incorporating {skill_name} with error handling. "
                    "Validate inputs and adhere to modular design patterns."
                )
                criteria = [
                    f"Implement complete feature workflow using {skill_name}",
                    "Handle edge cases and input validation errors gracefully",
                ]
            else:
                diff = TaskDifficulty.INTERMEDIATE
                title = f"Architecture Integration: {skill_name} Production Workflow"
                desc = (
                    f"Design and integrate an end-to-end component utilizing {skill_name}. "
                    "Include automated test suites and maintain architectural separation."
                )
                criteria = [
                    f"Complete production-grade integration of {skill_name}",
                    "Achieve verified test passes with full assertion coverage",
                ]

            if title.lower() in existing_titles:
                continue

            priority = (
                TaskPriority.HIGH if gap.severity == "high" else TaskPriority.MEDIUM
            )

            task = PersonalizedTask(
                task_id=f"tsk_{uuid.uuid4().hex[:10]}",
                developer_id=cleaned_id,
                title=title,
                description=desc,
                target_skill=skill_name,
                difficulty=diff,
                priority=priority,
                status=TaskStatus.GENERATED,
                estimated_minutes=45 if diff == TaskDifficulty.INTERMEDIATE else 30,
                target_role=target_role,
                prerequisite_skills=prereqs,
                reason=gap.importance_reason
                or f"Prerequisite competency required for {gap.target_skill}",
                acceptance_criteria=criteria,
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
