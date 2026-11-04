from __future__ import annotations

from collections import defaultdict, deque
from typing import TYPE_CHECKING

from prism.intelligence.models.skill_models import (
    RelationshipType,
    SkillGraphData,
    SkillRelationship,
)
from prism.logging.logger import get_logger

if TYPE_CHECKING:
    from prism.storage.repositories.base import SkillGraphRepository

logger = get_logger(__name__)


class SkillGraph:
    """Directed graph representing technical skills and their inter-relationships."""

    def __init__(self, repository: SkillGraphRepository | None = None) -> None:
        self._skills: set[str] = set()
        self._relationships: list[SkillRelationship] = []
        # from_skill (prereq) -> list of to_skills (dependents)
        self._prereq_to_dependents: dict[str, list[str]] = defaultdict(list)
        # to_skill (dependent) -> list of from_skills (prereqs)
        self._dependent_to_prereqs: dict[str, list[str]] = defaultdict(list)
        # Undirected related links
        self._related_map: dict[str, set[str]] = defaultdict(set)
        self._repository: SkillGraphRepository | None = repository

        if self._repository is not None:
            for s in self._repository.get_skills():
                self._skills.add(s)
            for r in self._repository.get_relationships():
                self._relationships.append(r)
                if r.relationship_type == RelationshipType.PREREQUISITE:
                    self._prereq_to_dependents[r.from_skill].append(r.to_skill)
                    self._dependent_to_prereqs[r.to_skill].append(r.from_skill)
                else:
                    self._related_map[r.from_skill].add(r.to_skill)
                    self._related_map[r.to_skill].add(r.from_skill)

    def add_skill(self, skill_name: str) -> None:
        """Register a technical skill in the graph."""
        cleaned = skill_name.strip()
        if not cleaned:
            raise ValueError("Skill name cannot be empty")
        self._skills.add(cleaned)
        if self._repository is not None:
            skill_id = cleaned.lower().replace(" ", "_")
            self._repository.register_skill(skill_id, cleaned)

    def has_skill(self, skill_name: str) -> bool:
        return skill_name.strip() in self._skills

    def get_skills(self) -> list[str]:
        return sorted(self._skills)

    def add_relationship(
        self,
        from_skill: str,
        to_skill: str,
        relationship_type: RelationshipType = RelationshipType.PREREQUISITE,
    ) -> None:
        """Add a directional relationship between two skills.

        For PREREQUISITE: from_skill is required before learning to_skill.
        """
        source = from_skill.strip()
        target = to_skill.strip()

        if not source or not target:
            raise ValueError("Both source and target skill must be non-empty")

        if source.lower() == target.lower():
            raise ValueError("A skill cannot have a relationship with itself")

        self.add_skill(source)
        self.add_skill(target)

        # Check for circular prerequisites
        if relationship_type == RelationshipType.PREREQUISITE and self._creates_cycle(
            source, target
        ):
            raise ValueError(
                f"Circular prerequisite detected: '{source}' -> '{target}' creates a cycle"
            )

        rel = SkillRelationship(
            from_skill=source,
            to_skill=target,
            relationship_type=relationship_type,
        )
        self._relationships.append(rel)
        if self._repository is not None:
            self._repository.add_relationship(rel)

        if relationship_type == RelationshipType.PREREQUISITE:
            self._prereq_to_dependents[source].append(target)
            self._dependent_to_prereqs[target].append(source)
        else:
            self._related_map[source].add(target)
            self._related_map[target].add(source)

        logger.debug(
            "Added skill relationship: %s -(%s)-> %s",
            source,
            relationship_type.value,
            target,
        )

    def _creates_cycle(self, proposed_prereq: str, proposed_dependent: str) -> bool:
        """Check if adding proposed_prereq -> proposed_dependent creates a cycle.

        Cycle exists if proposed_prereq is already reachable from proposed_dependent
        via existing prerequisite edges.
        """
        visited: set[str] = set()
        queue = deque([proposed_prereq])

        while queue:
            curr = queue.popleft()
            if curr == proposed_dependent:
                return True
            for parent in self._dependent_to_prereqs.get(curr, []):
                if parent not in visited:
                    visited.add(parent)
                    queue.append(parent)
        return False

    def get_prerequisites(self, skill_name: str, transitive: bool = True) -> list[str]:
        """Return prerequisites for a skill in topological dependency order."""
        target = skill_name.strip()
        if not self.has_skill(target):
            return []

        direct_prereqs = self._dependent_to_prereqs.get(target, [])
        if not transitive:
            return sorted(direct_prereqs)

        # Collect all transitive prerequisites using BFS/DFS
        all_prereqs: set[str] = set()
        queue = deque(direct_prereqs)
        while queue:
            curr = queue.popleft()
            if curr not in all_prereqs:
                all_prereqs.add(curr)
                queue.extend(self._dependent_to_prereqs.get(curr, []))

        # Return them sorted topologically so base prerequisites come first
        return self._topological_sort(all_prereqs)

    def get_dependents(self, skill_name: str) -> list[str]:
        """Return skills that directly depend on the given skill."""
        target = skill_name.strip()
        return sorted(self._prereq_to_dependents.get(target, []))

    def get_related_skills(self, skill_name: str) -> list[str]:
        """Return non-prerequisite related skills."""
        target = skill_name.strip()
        return sorted(self._related_map.get(target, set()))

    def _topological_sort(self, subset: set[str]) -> list[str]:
        """Order a subset of skills such that prerequisites appear before dependents."""
        in_degree: dict[str, int] = {s: 0 for s in subset}
        sub_dependents: dict[str, list[str]] = defaultdict(list)

        for s in subset:
            for dep in self._prereq_to_dependents.get(s, []):
                if dep in subset:
                    in_degree[dep] += 1
                    sub_dependents[s].append(dep)

        queue = deque([s for s in subset if in_degree[s] == 0])
        ordered: list[str] = []

        while queue:
            curr = queue.popleft()
            ordered.append(curr)
            for dep in sub_dependents.get(curr, []):
                in_degree[dep] -= 1
                if in_degree[dep] == 0:
                    queue.append(dep)

        # Any remaining nodes (in case of detached components)
        for s in subset:
            if s not in ordered:
                ordered.append(s)

        return ordered

    def export_graph(self) -> SkillGraphData:
        """Export current graph structure as a serializable model."""
        return SkillGraphData(
            skills=sorted(self._skills),
            relationships=list(self._relationships),
        )


class SkillGraphBuilder:
    """Builder providing a default curriculum skill graph and factory helpers."""

    @staticmethod
    def build_default_graph(
        repository: SkillGraphRepository | None = None,
    ) -> SkillGraph:
        """Construct a standardized software engineering technical skill graph."""
        graph = SkillGraph(repository=repository)

        # Machine Learning pathway
        # Python -> NumPy -> Pandas -> Statistics -> Machine Learning
        ml_edges = [
            ("Python", "NumPy"),
            ("NumPy", "Pandas"),
            ("Python", "Statistics"),
            ("Pandas", "Machine Learning"),
            ("Statistics", "Machine Learning"),
        ]
        for src, dst in ml_edges:
            graph.add_relationship(src, dst, RelationshipType.PREREQUISITE)

        # Web / Backend pathway
        # Python -> FastAPI -> REST APIs -> Software Architecture
        backend_edges = [
            ("Python", "FastAPI"),
            ("FastAPI", "REST APIs"),
            ("SQL", "Database Design"),
            ("Database Design", "Software Architecture"),
            ("REST APIs", "Software Architecture"),
            ("Python", "Object-Oriented Programming"),
            ("Object-Oriented Programming", "Software Architecture"),
            ("Data Structures", "Algorithms"),
            ("Algorithms", "Software Architecture"),
        ]
        for src, dst in backend_edges:
            graph.add_relationship(src, dst, RelationshipType.PREREQUISITE)

        # Frontend pathway
        frontend_edges = [
            ("HTML/CSS", "JavaScript"),
            ("JavaScript", "TypeScript"),
            ("TypeScript", "React"),
            ("Object-Oriented Programming", "Flutter"),
        ]
        for src, dst in frontend_edges:
            graph.add_relationship(src, dst, RelationshipType.PREREQUISITE)

        # Related skills
        related_pairs = [
            ("FastAPI", "REST APIs"),
            ("React", "Flutter"),
            ("Machine Learning", "Statistics"),
            ("SQL", "Database Design"),
        ]
        for s1, s2 in related_pairs:
            try:
                graph.add_relationship(s1, s2, RelationshipType.RELATED)
            except ValueError as err:
                logger.debug("Non-critical related edge skipped: %s", err)

        return graph
