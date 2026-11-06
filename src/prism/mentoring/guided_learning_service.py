import uuid
from datetime import UTC, datetime
from typing import Any

from prism.intelligence.models.task_platform_models import (
    GuidanceLevel,
    MentoringConversation,
    MentoringMessage,
)
from prism.intelligence.skill_tracker import SkillTracker
from prism.intelligence.task_recommendation_engine import (
    TaskRecommendationEngine,
)
from prism.learning.knowledge_gap_analyzer import KnowledgeGapAnalyzer
from prism.llm.service import LLMService
from prism.logging.logger import get_logger
from prism.rag.service import RAGService
from prism.storage.repositories.base import TaskPlatformRepository

logger = get_logger(__name__)

LEVEL_DESCRIPTIONS = {
    1: "Level 1: Conceptual explanation of the core principles.",
    2: "Level 2: Strategic approach and architectural design patterns.",
    3: "Level 3: Logical hint directing focus to key mechanics without code spoilers.",
    4: "Level 4: Step-by-step breakdown into smaller, actionable milestones.",
    5: "Level 5: Code concept illustrations with focused syntax patterns and examples.",
    6: "Level 6: Debugging guidance, failure analysis, and error diagnosis.",
}


class GuidedLearningService:
    """Interactive AI mentoring engine delivering 6 progressive guidance levels for assigned coding tasks."""

    def __init__(
        self,
        task_platform_repo: TaskPlatformRepository,
        task_engine: TaskRecommendationEngine,
        skill_tracker: SkillTracker,
        gap_analyzer: KnowledgeGapAnalyzer,
        llm_service: LLMService | None = None,
        rag_service: RAGService | None = None,
    ) -> None:
        self.task_platform_repo = task_platform_repo
        self.task_engine = task_engine
        self.skill_tracker = skill_tracker
        self.gap_analyzer = gap_analyzer
        self.llm_service = llm_service
        self.rag_service = rag_service

    def start_conversation(
        self,
        developer_id: str,
        task_id: str | None = None,
        initial_query: str | None = None,
    ) -> tuple[MentoringConversation, MentoringMessage | None]:
        """Start a task-linked interactive mentoring dialogue."""
        cleaned_dev_id = developer_id.strip()
        now = datetime.now(UTC)

        task_title = "General Mentoring"
        if task_id:
            task = self.task_engine.get_task(task_id)
            if task:
                task_title = f"Task: {task.title}"

        conversation = MentoringConversation(
            conversation_id=f"conv_{uuid.uuid4().hex[:12]}",
            task_id=task_id,
            developer_id=cleaned_dev_id,
            title=task_title,
            current_guidance_level=GuidanceLevel.CONCEPTUAL,
            status="active",
            created_at=now,
            updated_at=now,
        )
        self.task_platform_repo.create_conversation(conversation)

        first_response: MentoringMessage | None = None
        if initial_query:
            first_response = self.send_message(
                conversation_id=conversation.conversation_id,
                developer_message=initial_query,
                requested_level=GuidanceLevel.CONCEPTUAL,
            )

        return conversation, first_response

    def get_conversation(self, conversation_id: str) -> MentoringConversation | None:
        """Fetch conversation by ID."""
        return self.task_platform_repo.get_conversation(conversation_id)

    def get_history(
        self, conversation_id: str, limit: int = 100
    ) -> list[MentoringMessage]:
        """Fetch message history for a conversation."""
        return self.task_platform_repo.get_messages(conversation_id, limit=limit)

    def send_message(
        self,
        conversation_id: str,
        developer_message: str,
        requested_level: int | None = None,
        allow_solution: bool = False,
    ) -> MentoringMessage:
        """Process a developer query and deliver targeted, progressive mentoring guidance."""
        conv = self.task_platform_repo.get_conversation(conversation_id)
        if not conv:
            raise ValueError(f"Conversation '{conversation_id}' not found")

        # Determine effective guidance level
        effective_level = requested_level or conv.current_guidance_level
        if effective_level < 1:
            effective_level = 1
        elif effective_level > 6:
            effective_level = 6

        now = datetime.now(UTC)

        # 1. Save developer message
        user_msg = MentoringMessage(
            message_id=f"msg_{uuid.uuid4().hex[:12]}",
            conversation_id=conversation_id,
            sender="developer",
            content=developer_message.strip(),
            guidance_level=effective_level,
            metadata={"allow_solution": allow_solution},
            created_at=now,
        )
        self.task_platform_repo.save_message(user_msg)

        # 2. Gather Task & Learning Context
        task_context: dict[str, Any] = {}
        target_skill = "Software Engineering"
        task_hints: list[str] = []
        if conv.task_id:
            task = self.task_engine.get_task(conv.task_id)
            if task:
                target_skill = task.target_skill
                task_hints = task.hints
                task_context = {
                    "task_id": task.task_id,
                    "title": task.title,
                    "difficulty": str(task.difficulty),
                    "problem_statement": task.problem_statement or task.description,
                    "requirements": task.requirements,
                    "acceptance_criteria": task.acceptance_criteria,
                    "test_cases": [t.get("name") for t in task.test_cases],
                }

        # Submissions so far
        submissions = []
        if conv.task_id:
            submissions = self.task_platform_repo.get_submissions_for_task(conv.task_id)

        # Developer gaps
        profile = self.skill_tracker.get_profile(conv.developer_id)
        gaps = self.gap_analyzer.identify_gaps(profile, target_skill)

        # 3. Generate Mentor Response
        response_text = self._generate_guidance_response(
            level=effective_level,
            query=developer_message.strip(),
            task_context=task_context,
            target_skill=target_skill,
            task_hints=task_hints,
            attempts_count=len(submissions),
            gaps=[g.missing_skill for g in gaps],
            allow_solution=allow_solution,
        )

        mentor_msg = MentoringMessage(
            message_id=f"msg_{uuid.uuid4().hex[:12]}",
            conversation_id=conversation_id,
            sender="mentor",
            content=response_text,
            guidance_level=effective_level,
            metadata={
                "level_description": LEVEL_DESCRIPTIONS.get(effective_level, ""),
                "target_skill": target_skill,
                "allow_solution": allow_solution,
            },
            created_at=datetime.now(UTC),
        )
        self.task_platform_repo.save_message(mentor_msg)

        # Update conversation current guidance level if changed
        if effective_level != conv.current_guidance_level:
            self.task_platform_repo.update_conversation_level(
                conversation_id, effective_level
            )

        logger.info(
            "Mentoring guidance delivered | conv=%s | level=%d | dev=%s",
            conversation_id,
            effective_level,
            conv.developer_id,
        )
        return mentor_msg

    def request_hint(self, conversation_id: str) -> MentoringMessage:
        """Advance guidance to logical hints (Level 3) without spoilers."""
        return self.send_message(
            conversation_id=conversation_id,
            developer_message="Can you give me a progressive hint on how to proceed?",
            requested_level=GuidanceLevel.HINTS,
            allow_solution=False,
        )

    def request_step_by_step(self, conversation_id: str) -> MentoringMessage:
        """Break down the problem into smaller actionable steps (Level 4)."""
        return self.send_message(
            conversation_id=conversation_id,
            developer_message="Can you break this task down into smaller step-by-step milestones?",
            requested_level=GuidanceLevel.STEP_BY_STEP,
            allow_solution=False,
        )

    def request_debug_assistance(
        self,
        conversation_id: str,
        error_output: str,
        code_snippet: str | None = None,
    ) -> MentoringMessage:
        """Diagnose execution failure and guide developer through error understanding (Level 6)."""
        snippet_part = (
            f"\nCode Context:\n```python\n{code_snippet}\n```" if code_snippet else ""
        )
        query = f"I am encountering this error:\n```\n{error_output.strip()}\n```{snippet_part}\nHow can I debug and fix this?"
        return self.send_message(
            conversation_id=conversation_id,
            developer_message=query,
            requested_level=GuidanceLevel.DEBUGGING,
            allow_solution=False,
        )

    def _generate_guidance_response(
        self,
        level: int,
        query: str,
        task_context: dict[str, Any],
        target_skill: str,
        task_hints: list[str],
        attempts_count: int,
        gaps: list[str],
        allow_solution: bool,
    ) -> str:
        """Construct pedagogical response matching the exact guidance level."""
        task_title = task_context.get("title", f"{target_skill} Practice")
        criteria = task_context.get("acceptance_criteria", [])

        if level == GuidanceLevel.CONCEPTUAL:
            return (
                f"### Understanding the Core Concepts of {target_skill}\n\n"
                f"When working on **{task_title}**, the fundamental mental model to keep in mind is:\n\n"
                f"1. **Core Responsibility**: {target_skill} is designed to solve specific boundary and state management challenges.\n"
                f"2. **State & Flow**: Consider how data enters your module, where transformations occur, and how output invariants are maintained.\n"
                f"3. **Decoupling**: Keep data models separate from processing operations so individual units can be tested independently.\n\n"
                f"> **Think about**: What are the critical invariants that your implementation must uphold before you write any code?"
            )

        elif level == GuidanceLevel.APPROACH:
            return (
                f"### Recommended Approach for {task_title}\n\n"
                f"Here is a recommended architectural strategy to approach this challenge:\n\n"
                f"- **Phase 1: Input Validation**: Define strict validation at the entry boundary. Reject malformed data early with clear exceptions.\n"
                f"- **Phase 2: Core Transformation**: Implement the primary business logic cleanly without coupling it to external I/O.\n"
                f"- **Phase 3: Error & Edge Case Containment**: Identify edge cases (e.g. empty payloads, network timeouts, invalid types) and handle them defensively.\n"
                f"- **Phase 4: Output Contract**: Ensure the returned value or data structure strictly matches the required schema.\n\n"
                f"Try drafting the function signatures and contracts first before implementing the internal logic."
            )

        elif level == GuidanceLevel.HINTS:
            hint_item = (
                task_hints[0]
                if task_hints
                else f"Look closely at the acceptance criteria for {target_skill}."
            )
            return (
                f"### Progressive Hint (Level 3)\n\n"
                f"💡 **Key Insight**: {hint_item}\n\n"
                f"- Check how parameters are passed into your module.\n"
                f"- Verify whether you are returning the expected data type.\n"
                f"- Are all edge conditions (like zero, empty strings, or null objects) accounted for?\n\n"
                f"*Remember: Avoid hardcoding values—aim for an algorithmic solution that satisfies the acceptance checks.*"
            )

        elif level == GuidanceLevel.STEP_BY_STEP:
            reqs = task_context.get("requirements", [])
            steps_md = ""
            if reqs:
                steps_md = "\n".join(
                    f"{idx + 1}. **Step {idx + 1}**: {req}"
                    for idx, req in enumerate(reqs)
                )
            else:
                steps_md = (
                    f"1. **Step 1**: Scaffold the module file and import necessary standard libraries.\n"
                    f"2. **Step 2**: Define the main function/class with type annotations.\n"
                    f"3. **Step 3**: Implement boundary checks for input arguments.\n"
                    f"4. **Step 4**: Implement the core {target_skill} algorithm.\n"
                    f"5. **Step 5**: Write unit tests verifying expected output against edge cases."
                )

            return (
                f"### Step-by-Step Task Breakdown\n\n"
                f"To tackle **{task_title}** without getting overwhelmed, complete these steps sequentially:\n\n"
                f"{steps_md}\n\n"
                f"Focus on **Step 1 and Step 2** first. Once they run without syntax errors, proceed to the next milestone."
            )

        elif level == GuidanceLevel.CODE_CONCEPTS:
            return (
                f"### Code Concepts & Syntax Patterns for {target_skill}\n\n"
                f"Here is an illustrative syntax pattern demonstrating how similar problems are solved:\n\n"
                f"```python\n"
                f"# Pattern: Defensive execution and clear return contracts\n"
                f"def process_payload(data: dict) -> dict:\n"
                f"    if not isinstance(data, dict) or not data:\n"
                f'        raise ValueError("Payload cannot be empty")\n'
                f"    \n"
                f"    # Clean extraction and transformation\n"
                f"    transformed = {{k.strip().lower(): v for k, v in data.items()}}\n"
                f'    return {{"status": "success", "result": transformed}}\n'
                f"```\n\n"
                f"Apply this defensive pattern to your specific task requirements. Notice how the input is verified before processing."
            )

        else:  # GuidanceLevel.DEBUGGING
            if allow_solution:
                return (
                    f"### Complete Solution Reference (Explicitly Requested)\n\n"
                    f"Because you explicitly requested the complete solution, here is the reference implementation:\n\n"
                    f"```python\n"
                    f"# Complete Reference Implementation for {task_title}\n"
                    f"# Ensure all acceptance criteria are met\n"
                    f"class {target_skill.replace(' ', '')}Handler:\n"
                    f"    def execute(self, payload: Any) -> Any:\n"
                    f"        if payload is None:\n"
                    f'            raise ValueError("Invalid payload")\n'
                    f"        return payload\n"
                    f"```\n\n"
                    f"Study how this satisfies criteria: `{criteria}`."
                )

            return (
                "### Debugging & Error Analysis\n\n"
                "Let's isolate why this issue is occurring:\n\n"
                "1. **Identify the Point of Failure**: Look at the traceback line numbers to determine if the failure is at input parsing, type mismatch, or assertion failure.\n"
                "2. **Check Variable State**: Inspect what values your variables hold immediately before the crashing line.\n"
                "3. **Validate Assumptions**: Is an object `None` when you expected a dictionary or list? Are you indexing beyond the length of a sequence?\n\n"
                "👉 **Next debugging step**: Add print statements or use `pytest -vv` to inspect the exact failure diff. What value did your function return vs what was expected?"
            )
