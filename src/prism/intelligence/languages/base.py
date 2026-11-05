from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ConceptExtraction:
    """Extracted programming concept and subconcept."""

    concept: str
    subconcept: str | None = None
    related_skill: str | None = None
    confidence: float = 0.85


@dataclass
class CodeAnalysisResult:
    """Structured code analysis result produced by a language adapter."""

    language: str
    frameworks: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    concepts: list[ConceptExtraction] = field(default_factory=list)
    complexity: str = "medium"


class LanguageAdapter(Protocol):
    """Protocol implemented by every language adapter."""

    @property
    def language(self) -> str:
        """Canonical language name."""
        ...

    @property
    def file_extensions(self) -> tuple[str, ...]:
        """Recognized file extensions (with leading dot)."""
        ...

    def detect_frameworks(self, content: str, file_path: str = "") -> list[str]:
        """Detect tech frameworks used in the source content or path."""
        ...

    def extract_concepts(
        self, content: str, file_path: str = ""
    ) -> list[ConceptExtraction]:
        """Extract high-level concepts and subconcepts."""
        ...

    def analyze_code(self, content: str, file_path: str = "") -> CodeAnalysisResult:
        """Analyze code structure, frameworks, and concepts."""
        ...
