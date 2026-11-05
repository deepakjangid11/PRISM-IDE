import re
from pathlib import Path

from prism.intelligence.languages.adapters import (
    CppAdapter,
    CSharpAdapter,
    DartAdapter,
    DataScienceAdapter,
    GenericFallbackAdapter,
    GoAdapter,
    HtmlCssAdapter,
    JavaAdapter,
    KotlinAdapter,
    PhpAdapter,
    PythonAdapter,
    RubyAdapter,
    RustAdapter,
    SqlAdapter,
    SwiftAdapter,
    TypeScriptJavaScriptAdapter,
)
from prism.intelligence.languages.base import LanguageAdapter
from prism.intelligence.models.activity_classification_models import (
    ProgrammingLanguage,
)

SHEBANG_MAP = {
    re.compile(r"^#!\s*/.*\bpython[0-9.]*\b"): ProgrammingLanguage.PYTHON.value,
    re.compile(r"^#!\s*/.*\bnode\b"): ProgrammingLanguage.JAVASCRIPT.value,
    re.compile(r"^#!\s*/.*\bruby\b"): ProgrammingLanguage.RUBY.value,
    re.compile(r"^#!\s*/.*\bphp\b"): ProgrammingLanguage.PHP.value,
    re.compile(r"^#!\s*/.*\bsh\b|^#!\s*/.*\bbash\b"): "Shell",
}


class LanguageAdapterRegistry:
    """Central registry and cache for multi-language detection and adapters."""

    def __init__(self) -> None:
        self._adapters: list[LanguageAdapter] = [
            PythonAdapter(),
            TypeScriptJavaScriptAdapter(),
            JavaAdapter(),
            CSharpAdapter(),
            GoAdapter(),
            RustAdapter(),
            CppAdapter(),
            PhpAdapter(),
            RubyAdapter(),
            KotlinAdapter(),
            SwiftAdapter(),
            DartAdapter(),
            SqlAdapter(),
            HtmlCssAdapter(),
            DataScienceAdapter(),
        ]
        self._fallback_adapter = GenericFallbackAdapter()
        self._ext_map: dict[str, LanguageAdapter] = {}
        for adapter in self._adapters:
            for ext in adapter.file_extensions:
                self._ext_map[ext.lower()] = adapter

    def get_adapter_for_file(
        self, file_path: str, content: str | None = None
    ) -> LanguageAdapter:
        """Find the most appropriate adapter for a file."""
        ext = Path(file_path).suffix.lower() if file_path else ""
        if ext in self._ext_map:
            return self._ext_map[ext]

        # Check shebang or keywords if content provided
        if content:
            lang = self._detect_from_content(content)
            if lang:
                for adapter in self._adapters:
                    if adapter.language.lower() == lang.lower():
                        return adapter

        return self._fallback_adapter

    def detect_language(self, file_path: str | None, content: str | None = None) -> str:
        """Lightweight and cached language detection."""
        if not file_path and not content:
            return ProgrammingLanguage.UNKNOWN.value

        if file_path:
            ext = Path(file_path).suffix.lower()
            if ext in self._ext_map:
                adapter = self._ext_map[ext]
                # Specific disambiguation
                if ext in (".ts", ".tsx"):
                    return ProgrammingLanguage.TYPESCRIPT.value
                if ext in (".js", ".jsx", ".mjs", ".cjs"):
                    return ProgrammingLanguage.JAVASCRIPT.value
                if ext in (".css", ".scss", ".sass", ".less"):
                    return ProgrammingLanguage.CSS.value
                if ext in (".html", ".htm"):
                    return ProgrammingLanguage.HTML.value
                if ext == ".jl":
                    return ProgrammingLanguage.JULIA.value
                if ext in (".r", ".rmd"):
                    return ProgrammingLanguage.R.value
                if ext in (".c", ".h"):
                    return ProgrammingLanguage.C.value
                if ext in (".cpp", ".cc", ".cxx", ".hpp"):
                    return ProgrammingLanguage.CPP.value
                return adapter.language

        if content:
            detected = self._detect_from_content(content)
            if detected:
                return detected

        return ProgrammingLanguage.UNKNOWN.value

    def _detect_from_content(self, content: str) -> str | None:
        first_line = content.splitlines()[0] if content else ""
        for pattern, lang in SHEBANG_MAP.items():
            if pattern.search(first_line):
                return lang

        # Quick structural heuristics
        if re.search(
            r"\bpackage\s+[a-z0-9_]+;\s*|\bpublic\s+class\s+[A-Za-z0-9_]+", content
        ):
            return ProgrammingLanguage.JAVA.value
        if re.search(r"\bdef\s+[a-z0-9_]+\s*\(.*?\):|\bimport\s+[a-z0-9_]+", content):
            return ProgrammingLanguage.PYTHON.value
        if re.search(
            r"\bimport\s+React\b|\bconst\s+[a-zA-Z0-9_]+\s*=\s*\(.*?\)\s*=>", content
        ):
            return ProgrammingLanguage.TYPESCRIPT.value
        if re.search(r"\bfunc\s+[A-Za-z0-9_]+\s*\(.*?\)", content):
            return ProgrammingLanguage.GO.value
        if re.search(r"\bfn\s+[a-z0-9_]+\s*\(.*?\)\s*->|\bpub\s+fn\b", content):
            return ProgrammingLanguage.RUST.value
        if re.search(
            r"\bSELECT\s+.+?\s+FROM\s+|\bCREATE\s+TABLE\b", content, re.IGNORECASE
        ):
            return ProgrammingLanguage.SQL.value

        return None


# Global registry singleton for performance
language_registry = LanguageAdapterRegistry()
