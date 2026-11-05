import ast
import re
from typing import ClassVar

from prism.intelligence.languages.base import (
    CodeAnalysisResult,
    ConceptExtraction,
)
from prism.intelligence.models.activity_classification_models import (
    ProgrammingLanguage,
)


class BasePatternAdapter:
    """Base class for language adapters using efficient pattern matching and heuristics."""

    language_name: str = ProgrammingLanguage.UNKNOWN.value
    extensions: tuple[str, ...] = ()
    framework_patterns: ClassVar[dict[str, re.Pattern[str]]] = {}
    concept_rules: ClassVar[list[tuple[re.Pattern[str], str, str, str, float]]] = []

    @property
    def language(self) -> str:
        return self.language_name

    @property
    def file_extensions(self) -> tuple[str, ...]:
        return self.extensions

    def detect_frameworks(self, content: str, file_path: str = "") -> list[str]:
        found: set[str] = set()
        text = f"{file_path}\n{content}"
        for name, pattern in self.framework_patterns.items():
            if pattern.search(text):
                found.add(name)
        return sorted(found)

    def extract_concepts(
        self, content: str, file_path: str = ""
    ) -> list[ConceptExtraction]:
        extractions: list[ConceptExtraction] = []
        seen: set[str] = set()

        for pattern, concept, subconcept, skill, conf in self.concept_rules:
            if pattern.search(content):
                key = f"{concept}:{subconcept}"
                if key not in seen:
                    seen.add(key)
                    extractions.append(
                        ConceptExtraction(
                            concept=concept,
                            subconcept=subconcept if subconcept else None,
                            related_skill=skill if skill else None,
                            confidence=conf,
                        )
                    )

        if not extractions:
            extractions.append(
                ConceptExtraction(
                    concept="General Programming",
                    subconcept="Syntax & Logic",
                    related_skill=f"{self.language} Fundamentals",
                    confidence=0.7,
                )
            )

        return extractions

    def analyze_code(self, content: str, file_path: str = "") -> CodeAnalysisResult:
        frameworks = self.detect_frameworks(content, file_path)
        concepts = self.extract_concepts(content, file_path)
        classes, functions, imports = self._extract_symbols(content)

        line_count = len(content.splitlines())
        branch_count = len(
            re.findall(r"\b(if|else|switch|for|while|try|catch)\b", content)
        )
        if line_count > 300 or branch_count > 25:
            complexity = "high"
        elif line_count > 80 or branch_count > 8:
            complexity = "medium"
        else:
            complexity = "low"

        return CodeAnalysisResult(
            language=self.language,
            frameworks=frameworks,
            classes=classes,
            functions=functions,
            imports=imports,
            concepts=concepts,
            complexity=complexity,
        )

    def _extract_symbols(self, content: str) -> tuple[list[str], list[str], list[str]]:
        classes = [
            m.group(1) for m in re.finditer(r"\bclass\s+([A-Za-z0-9_]+)", content)
        ]
        functions = [
            m.group(1)
            for m in re.finditer(
                r"\b(?:def|function|func|fn)\s+([A-Za-z0-9_]+)", content
            )
        ]
        imports: list[str] = []
        return classes[:30], functions[:50], imports[:30]


class PythonAdapter(BasePatternAdapter):
    """Python language adapter using ast parsing when available with pattern fallback."""

    language_name = ProgrammingLanguage.PYTHON.value
    extensions = (".py", ".pyi", ".pyw")
    framework_patterns: ClassVar[dict[str, re.Pattern[str]]] = {
        "FastAPI": re.compile(
            r"\b(from\s+fastapi|import\s+fastapi|FastAPI\(|APIRouter\()", re.IGNORECASE
        ),
        "Flask": re.compile(
            r"\b(from\s+flask|import\s+flask|Flask\(__name__\))", re.IGNORECASE
        ),
        "Django": re.compile(
            r"\b(from\s+django|import\s+django|models\.Model|views\.)", re.IGNORECASE
        ),
        "SQLAlchemy": re.compile(
            r"\b(from\s+sqlalchemy|import\s+sqlalchemy|mapped_column|declarative_base)",
            re.IGNORECASE,
        ),
        "Pytest": re.compile(
            r"\b(import\s+pytest|def\s+test_|@pytest\.fixture)", re.IGNORECASE
        ),
        "Pandas": re.compile(
            r"\b(import\s+pandas|from\s+pandas|pd\.DataFrame)", re.IGNORECASE
        ),
        "PyTorch": re.compile(
            r"\b(import\s+torch|from\s+torch|nn\.Module)", re.IGNORECASE
        ),
    }
    concept_rules: ClassVar[list[tuple[re.Pattern[str], str, str, str, float]]] = [
        (
            re.compile(r"\bclass\s+[A-Za-z0-9_]+(?:\([A-Za-z0-9_,\s]+\))?:"),
            "Object-Oriented Programming",
            "Inheritance & Classes",
            "Python OOP",
            0.95,
        ),
        (
            re.compile(r"\basync\s+(?:def|with|for)\b"),
            "Asynchronous Programming",
            "Coroutines & Event Loops",
            "Python AsyncIO",
            0.95,
        ),
        (
            re.compile(r"@\w+"),
            "Metaprogramming",
            "Decorators",
            "Python Decorators",
            0.90,
        ),
        (
            re.compile(r"\[.+?\s+for\s+.+?\s+in\s+.+?\]"),
            "Functional Programming",
            "List Comprehensions",
            "Python Idioms",
            0.85,
        ),
        (
            re.compile(r"\byield\b"),
            "Generators & Iteration",
            "Yield Expressions",
            "Python Generators",
            0.90,
        ),
        (
            re.compile(r"\bdef\s+test_[A-Za-z0-9_]+"),
            "Automated Testing",
            "Unit Tests",
            "Python Testing",
            0.95,
        ),
    ]

    def analyze_code(self, content: str, file_path: str = "") -> CodeAnalysisResult:
        classes: list[str] = []
        functions: list[str] = []
        imports: list[str] = []

        try:
            tree = ast.parse(content, filename=file_path or "<unknown>")
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    functions.append(node.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)
        except SyntaxError, ValueError, TypeError:
            classes, functions, imports = self._extract_symbols(content)

        frameworks = self.detect_frameworks(content, file_path)
        concepts = self.extract_concepts(content, file_path)

        line_count = len(content.splitlines())
        complexity = (
            "high" if line_count > 300 else ("medium" if line_count > 80 else "low")
        )

        return CodeAnalysisResult(
            language=self.language,
            frameworks=frameworks,
            classes=classes[:30],
            functions=functions[:50],
            imports=sorted(set(imports))[:30],
            concepts=concepts,
            complexity=complexity,
        )


class TypeScriptJavaScriptAdapter(BasePatternAdapter):
    """JavaScript and TypeScript adapter."""

    language_name = ProgrammingLanguage.TYPESCRIPT.value
    extensions = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
    framework_patterns: ClassVar[dict[str, re.Pattern[str]]] = {
        "React": re.compile(
            r"\b(import\s+React|from\s+['\"]react['\"]|useState|useEffect|useContext|JSX\.Element)",
            re.IGNORECASE,
        ),
        "Vue": re.compile(
            r"\b(from\s+['\"]vue['\"]|defineComponent|ref\(|reactive\()", re.IGNORECASE
        ),
        "Angular": re.compile(
            r"\b(@Component|@Injectable|@NgModule|from\s+['\"]@angular)", re.IGNORECASE
        ),
        "Express": re.compile(
            r"\b(express\(|require\(['\"]express['\"]\)|Router\(\))", re.IGNORECASE
        ),
        "Next.js": re.compile(
            r"\b(from\s+['\"]next/|getStaticProps|getServerSideProps)", re.IGNORECASE
        ),
        "Node.js": re.compile(
            r"\b(require\(['\"]node:|process\.env|fs\.promises)", re.IGNORECASE
        ),
        "Jest": re.compile(r"\b(describe\(|test\(|it\(|expect\()", re.IGNORECASE),
    }
    concept_rules: ClassVar[list[tuple[re.Pattern[str], str, str, str, float]]] = [
        (
            re.compile(r"(?:interface|type)\s+[A-Za-z0-9_]+\s*="),
            "Type Systems",
            "Static Typing",
            "TypeScript Types",
            0.95,
        ),
        (
            re.compile(r"\b(useState|useEffect|useMemo|useCallback)\b"),
            "Component Architecture",
            "React Hooks",
            "React",
            0.95,
        ),
        (
            re.compile(r"\bclass\s+[A-Za-z0-9_]+\s+extends\b"),
            "Object-Oriented Programming",
            "Class Inheritance",
            "JavaScript OOP",
            0.90,
        ),
        (
            re.compile(r"\basync\s+(?:function|\()|\bawait\s+"),
            "Asynchronous Programming",
            "Promises & Async/Await",
            "Async JS",
            0.95,
        ),
        (
            re.compile(r"\b(export\s+default|export\s+const|import\s+.+?\s+from)\b"),
            "Modular Architecture",
            "ES Modules",
            "JavaScript Modules",
            0.90,
        ),
        (
            re.compile(r"\b(describe|test|it)\s*\("),
            "Automated Testing",
            "Test Suites",
            "JavaScript Testing",
            0.90,
        ),
    ]

    def analyze_code(self, content: str, file_path: str = "") -> CodeAnalysisResult:
        lang = (
            ProgrammingLanguage.TYPESCRIPT.value
            if file_path.endswith((".ts", ".tsx"))
            else ProgrammingLanguage.JAVASCRIPT.value
        )
        self.language_name = lang
        result = super().analyze_code(content, file_path)
        result.language = lang
        return result


class JavaAdapter(BasePatternAdapter):
    """Java language adapter."""

    language_name = ProgrammingLanguage.JAVA.value
    extensions = (".java",)
    framework_patterns: ClassVar[dict[str, re.Pattern[str]]] = {
        "Spring Boot": re.compile(
            r"@SpringBootApplication|@RestController|@Service|@Repository|@Autowired",
            re.IGNORECASE,
        ),
        "Hibernate": re.compile(
            r"@Entity|@Table|@Id|@GeneratedValue|EntityManager", re.IGNORECASE
        ),
        "JUnit": re.compile(r"@Test|@BeforeEach|@ExtendWith|org\.junit", re.IGNORECASE),
    }
    concept_rules: ClassVar[list[tuple[re.Pattern[str], str, str, str, float]]] = [
        (
            re.compile(r"\binterface\s+[A-Za-z0-9_]+"),
            "Object-Oriented Programming",
            "Interfaces",
            "Java OOP",
            0.95,
        ),
        (
            re.compile(r"\bclass\s+[A-Za-z0-9_]+\s+(?:extends|implements)\b"),
            "Object-Oriented Programming",
            "Polymorphism & Inheritance",
            "Java OOP",
            0.95,
        ),
        (
            re.compile(r"@(?:Autowired|Inject)"),
            "Software Architecture",
            "Dependency Injection",
            "Spring Architecture",
            0.95,
        ),
        (
            re.compile(r"\bCompletableFuture|Thread|synchronized\b"),
            "Concurrency",
            "Multithreading",
            "Java Concurrency",
            0.90,
        ),
        (
            re.compile(r"\bStream<|(?:\.stream\(\))"),
            "Functional Programming",
            "Java Streams API",
            "Java Streams",
            0.90,
        ),
        (re.compile(r"@Test\b"), "Automated Testing", "Unit Testing", "JUnit", 0.95),
    ]


class CSharpAdapter(BasePatternAdapter):
    """C# (.NET) adapter."""

    language_name = ProgrammingLanguage.CSHARP.value
    extensions = (".cs",)
    framework_patterns: ClassVar[dict[str, re.Pattern[str]]] = {
        "ASP.NET": re.compile(
            r"Microsoft\.AspNetCore|ControllerBase|WebApplication|builder\.Services",
            re.IGNORECASE,
        ),
        "Entity Framework": re.compile(
            r"DbContext|DbSet<|Microsoft\.EntityFrameworkCore", re.IGNORECASE
        ),
        "xUnit": re.compile(r"\[Fact\]|\[Theory\]|Xunit", re.IGNORECASE),
    }
    concept_rules: ClassVar[list[tuple[re.Pattern[str], str, str, str, float]]] = [
        (
            re.compile(r"\basync\s+Task|\bawait\b"),
            "Asynchronous Programming",
            "Task-based Asynchronous Pattern",
            "C# Async",
            0.95,
        ),
        (
            re.compile(r"\bSelect\(|\bWhere\(|\.ToList\(\)"),
            "Data Querying",
            "LINQ",
            "C# LINQ",
            0.90,
        ),
        (
            re.compile(r"\binterface\s+I[A-Za-z0-9_]+"),
            "Object-Oriented Programming",
            "Interfaces",
            "C# OOP",
            0.95,
        ),
        (
            re.compile(r"\[(?:Fact|Theory|TestMethod)\]"),
            "Automated Testing",
            "Unit Testing",
            "C# Testing",
            0.95,
        ),
    ]


class GoAdapter(BasePatternAdapter):
    """Go language adapter."""

    language_name = ProgrammingLanguage.GO.value
    extensions = (".go",)
    framework_patterns: ClassVar[dict[str, re.Pattern[str]]] = {
        "Gin": re.compile(r"github\.com/gin-gonic/gin|gin\.Default\(", re.IGNORECASE),
        "Echo": re.compile(r"github\.com/labstack/echo|echo\.New\(", re.IGNORECASE),
        "GORM": re.compile(r"gorm\.io/gorm|gorm\.DB", re.IGNORECASE),
    }
    concept_rules: ClassVar[list[tuple[re.Pattern[str], str, str, str, float]]] = [
        (
            re.compile(r"\bgo\s+[A-Za-z0-9_]+\s*\("),
            "Concurrency",
            "Goroutines",
            "Go Concurrency",
            0.95,
        ),
        (
            re.compile(r"\bchan\s+[A-Za-z0-9_]+|\bselect\s*\{"),
            "Concurrency",
            "Channels",
            "Go Concurrency",
            0.95,
        ),
        (
            re.compile(r"\btype\s+[A-Za-z0-9_]+\s+interface\b"),
            "Object-Oriented Programming",
            "Interfaces",
            "Go Interfaces",
            0.95,
        ),
        (
            re.compile(r"\btype\s+[A-Za-z0-9_]+\s+struct\b"),
            "Data Modeling",
            "Structs & Composition",
            "Go Structs",
            0.90,
        ),
        (
            re.compile(r"\bfunc\s+Test[A-Za-z0-9_]+\s*\("),
            "Automated Testing",
            "Go Testing",
            "Go Testing",
            0.95,
        ),
    ]


class RustAdapter(BasePatternAdapter):
    """Rust language adapter."""

    language_name = ProgrammingLanguage.RUST.value
    extensions = (".rs",)
    framework_patterns: ClassVar[dict[str, re.Pattern[str]]] = {
        "Tokio": re.compile(r"tokio::|#\[tokio::main\]", re.IGNORECASE),
        "Actix": re.compile(r"actix_web::", re.IGNORECASE),
        "Rocket": re.compile(r"rocket::", re.IGNORECASE),
        "Serde": re.compile(
            r"serde::|derive\(Serialize|derive\(Deserialize", re.IGNORECASE
        ),
    }
    concept_rules: ClassVar[list[tuple[re.Pattern[str], str, str, str, float]]] = [
        (
            re.compile(r"\btrait\s+[A-Za-z0-9_]+"),
            "Type Systems",
            "Traits",
            "Rust Traits",
            0.95,
        ),
        (
            re.compile(r"&mut\s+|&'static\s+|\bArc<|\bRc<|\bMutex<"),
            "Memory Safety",
            "Borrowing & Lifetimes",
            "Rust Ownership",
            0.95,
        ),
        (
            re.compile(r"\bmatch\s+.+?\{"),
            "Functional Programming",
            "Pattern Matching",
            "Rust Patterns",
            0.90,
        ),
        (
            re.compile(r"#\[test\]"),
            "Automated Testing",
            "Unit Testing",
            "Rust Testing",
            0.95,
        ),
    ]


class CppAdapter(BasePatternAdapter):
    """C and C++ language adapter."""

    language_name = ProgrammingLanguage.CPP.value
    extensions = (".cpp", ".cc", ".cxx", ".c", ".h", ".hpp")
    framework_patterns: ClassVar[dict[str, re.Pattern[str]]] = {
        "Qt": re.compile(r"#include\s+<Q|QObject|Q_OBJECT", re.IGNORECASE),
        "Boost": re.compile(r"#include\s+<boost/", re.IGNORECASE),
        "STL": re.compile(
            r"#include\s+<(?:vector|map|string|algorithm)>", re.IGNORECASE
        ),
    }
    concept_rules: ClassVar[list[tuple[re.Pattern[str], str, str, str, float]]] = [
        (
            re.compile(r"template\s*<typename"),
            "Generic Programming",
            "Templates",
            "C++ Templates",
            0.95,
        ),
        (
            re.compile(r"\bstd::unique_ptr|std::shared_ptr\b"),
            "Memory Management",
            "Smart Pointers (RAII)",
            "Modern C++",
            0.95,
        ),
        (
            re.compile(r"\b(?:malloc|free)\b|(?:\*\s*[A-Za-z0-9_]+)"),
            "Systems Programming",
            "Pointers & Dynamic Allocation",
            "C/C++ Memory",
            0.90,
        ),
    ]


class PhpAdapter(BasePatternAdapter):
    """PHP language adapter."""

    language_name = ProgrammingLanguage.PHP.value
    extensions = (".php",)
    framework_patterns: ClassVar[dict[str, re.Pattern[str]]] = {
        "Laravel": re.compile(r"Illuminate\\|artisan|Route::get", re.IGNORECASE),
        "Symfony": re.compile(r"Symfony\\Component", re.IGNORECASE),
        "WordPress": re.compile(r"add_action\(|add_filter\(|wp_", re.IGNORECASE),
    }
    concept_rules: ClassVar[list[tuple[re.Pattern[str], str, str, str, float]]] = [
        (
            re.compile(r"\btrait\s+[A-Za-z0-9_]+"),
            "Object-Oriented Programming",
            "Traits",
            "PHP OOP",
            0.90,
        ),
        (
            re.compile(r"\bclass\s+[A-Za-z0-9_]+\s+extends"),
            "Object-Oriented Programming",
            "Inheritance",
            "PHP OOP",
            0.90,
        ),
    ]


class RubyAdapter(BasePatternAdapter):
    """Ruby language adapter."""

    language_name = ProgrammingLanguage.RUBY.value
    extensions = (".rb", ".rake")
    framework_patterns: ClassVar[dict[str, re.Pattern[str]]] = {
        "Ruby on Rails": re.compile(
            r"ActiveRecord::Base|ActionController::Base|routes\.draw", re.IGNORECASE
        ),
        "Sinatra": re.compile(
            r"require\s+['\"]sinatra['\"]|get\s+['\"]/", re.IGNORECASE
        ),
        "RSpec": re.compile(r"RSpec\.describe|describe\s+.+?\s+do", re.IGNORECASE),
    }
    concept_rules: ClassVar[list[tuple[re.Pattern[str], str, str, str, float]]] = [
        (
            re.compile(r"\bdef\s+[A-Za-z0-9_]+"),
            "Object-Oriented Programming",
            "Methods & Classes",
            "Ruby OOP",
            0.85,
        ),
        (
            re.compile(r"\byield\b|\.each\s+do"),
            "Functional Programming",
            "Blocks & Procs",
            "Ruby Blocks",
            0.90,
        ),
    ]


class KotlinAdapter(BasePatternAdapter):
    """Kotlin language adapter."""

    language_name = ProgrammingLanguage.KOTLIN.value
    extensions = (".kt", ".kts")
    framework_patterns: ClassVar[dict[str, re.Pattern[str]]] = {
        "Android SDK": re.compile(
            r"android\.app\.|androidx\.|findViewById|setContentView", re.IGNORECASE
        ),
        "Jetpack Compose": re.compile(
            r"@Composable|remember\s*\{|Surface\(", re.IGNORECASE
        ),
        "Ktor": re.compile(r"io\.ktor\.", re.IGNORECASE),
    }
    concept_rules: ClassVar[list[tuple[re.Pattern[str], str, str, str, float]]] = [
        (
            re.compile(r"\bsuspend\s+fun\b"),
            "Concurrency",
            "Coroutines",
            "Kotlin Coroutines",
            0.95,
        ),
        (
            re.compile(r"@Composable"),
            "Mobile Development",
            "Declarative UI",
            "Jetpack Compose",
            0.95,
        ),
        (
            re.compile(r"\bdata\s+class\b"),
            "Data Modeling",
            "Data Classes",
            "Kotlin OOP",
            0.90,
        ),
    ]


class SwiftAdapter(BasePatternAdapter):
    """Swift language adapter."""

    language_name = ProgrammingLanguage.SWIFT.value
    extensions = (".swift",)
    framework_patterns: ClassVar[dict[str, re.Pattern[str]]] = {
        "SwiftUI": re.compile(
            r"import\s+SwiftUI|View\s*\{|@State|@Binding", re.IGNORECASE
        ),
        "UIKit": re.compile(r"import\s+UIKit|UIViewController|UIView", re.IGNORECASE),
    }
    concept_rules: ClassVar[list[tuple[re.Pattern[str], str, str, str, float]]] = [
        (
            re.compile(r"\bprotocol\s+[A-Za-z0-9_]+"),
            "Protocol-Oriented Programming",
            "Protocols",
            "Swift Protocols",
            0.95,
        ),
        (
            re.compile(r"@(?:State|Binding|ObservedObject|Published)"),
            "Declarative UI",
            "State Management",
            "SwiftUI",
            0.95,
        ),
    ]


class DartAdapter(BasePatternAdapter):
    """Dart language adapter."""

    language_name = ProgrammingLanguage.DART.value
    extensions = (".dart",)
    framework_patterns: ClassVar[dict[str, re.Pattern[str]]] = {
        "Flutter": re.compile(
            r"package:flutter/|StatelessWidget|StatefulWidget|Widget\s+build\(",
            re.IGNORECASE,
        ),
    }
    concept_rules: ClassVar[list[tuple[re.Pattern[str], str, str, str, float]]] = [
        (
            re.compile(
                r"class\s+[A-Za-z0-9_]+\s+extends\s+(?:Stateless|Stateful)Widget"
            ),
            "Mobile Development",
            "Widget Component Architecture",
            "Flutter Widgets",
            0.95,
        ),
        (
            re.compile(r"\bFuture<|async\s*\{|\bawait\b"),
            "Asynchronous Programming",
            "Futures & Streams",
            "Dart Async",
            0.90,
        ),
    ]


class SqlAdapter(BasePatternAdapter):
    """SQL language adapter."""

    language_name = ProgrammingLanguage.SQL.value
    extensions = (".sql", ".psql")
    framework_patterns: ClassVar[dict[str, re.Pattern[str]]] = {
        "MySQL": re.compile(r"ENGINE=InnoDB|AUTO_INCREMENT|mysql", re.IGNORECASE),
        "PostgreSQL": re.compile(
            r"SERIAL|RETURNING|CREATE\s+OR\s+REPLACE\s+FUNCTION", re.IGNORECASE
        ),
    }
    concept_rules: ClassVar[list[tuple[re.Pattern[str], str, str, str, float]]] = [
        (
            re.compile(r"\bCREATE\s+TABLE\b", re.IGNORECASE),
            "Database Design",
            "DDL Schema Definition",
            "SQL DDL",
            0.95,
        ),
        (
            re.compile(r"\b(?:INNER|LEFT|RIGHT|FULL)\s+JOIN\b", re.IGNORECASE),
            "Database Querying",
            "Relational Joins",
            "SQL Joins",
            0.95,
        ),
        (
            re.compile(r"\bCREATE\s+(?:UNIQUE\s+)?INDEX\b", re.IGNORECASE),
            "Database Performance",
            "Indexing Strategies",
            "SQL Indexing",
            0.95,
        ),
        (
            re.compile(r"\bSTART\s+TRANSACTION\b|\bBEGIN\b|\bCOMMIT\b", re.IGNORECASE),
            "Transactions & ACID",
            "Transaction Management",
            "Database Transactions",
            0.95,
        ),
    ]


class HtmlCssAdapter(BasePatternAdapter):
    """HTML and CSS adapter."""

    language_name = ProgrammingLanguage.HTML.value
    extensions = (".html", ".htm", ".css", ".scss", ".sass", ".less")
    framework_patterns: ClassVar[dict[str, re.Pattern[str]]] = {
        "Tailwind": re.compile(
            r"class=[\"'].*?\b(?:flex|grid|p-\d|m-\d|text-)\b", re.IGNORECASE
        ),
        "Bootstrap": re.compile(
            r"class=[\"'].*?\b(?:container|row|col-)\b", re.IGNORECASE
        ),
    }
    concept_rules: ClassVar[list[tuple[re.Pattern[str], str, str, str, float]]] = [
        (
            re.compile(r"display:\s*flex|flex-direction", re.IGNORECASE),
            "Responsive Layout",
            "Flexbox",
            "CSS Layout",
            0.90,
        ),
        (
            re.compile(r"display:\s*grid|grid-template", re.IGNORECASE),
            "Responsive Layout",
            "CSS Grid",
            "CSS Layout",
            0.90,
        ),
        (
            re.compile(r"@media\s*\([^\)]+\)", re.IGNORECASE),
            "Responsive Design",
            "Media Queries",
            "Responsive Web Design",
            0.90,
        ),
    ]

    def analyze_code(self, content: str, file_path: str = "") -> CodeAnalysisResult:
        lang = (
            ProgrammingLanguage.CSS.value
            if file_path.endswith((".css", ".scss", ".sass", ".less"))
            else ProgrammingLanguage.HTML.value
        )
        self.language_name = lang
        res = super().analyze_code(content, file_path)
        res.language = lang
        return res


class DataScienceAdapter(BasePatternAdapter):
    """R and Julia language adapter."""

    language_name = ProgrammingLanguage.R.value
    extensions = (".r", ".rmd", ".jl")
    framework_patterns: ClassVar[dict[str, re.Pattern[str]]] = {
        "Tidyverse": re.compile(
            r"library\(tidyverse\)|library\(dplyr\)", re.IGNORECASE
        ),
        "ggplot2": re.compile(r"library\(ggplot2\)|ggplot\(", re.IGNORECASE),
    }
    concept_rules: ClassVar[list[tuple[re.Pattern[str], str, str, str, float]]] = [
        (
            re.compile(r"%\>%|\bdata\.frame\b|\btibble\b"),
            "Data Manipulation",
            "Data Frames & Pipelines",
            "R Data Science",
            0.90,
        ),
        (
            re.compile(r"ggplot\(|geom_\w+"),
            "Data Visualization",
            "Grammar of Graphics",
            "R Visualization",
            0.90,
        ),
    ]

    def analyze_code(self, content: str, file_path: str = "") -> CodeAnalysisResult:
        lang = (
            ProgrammingLanguage.JULIA.value
            if file_path.endswith(".jl")
            else ProgrammingLanguage.R.value
        )
        self.language_name = lang
        res = super().analyze_code(content, file_path)
        res.language = lang
        return res


class GenericFallbackAdapter(BasePatternAdapter):
    """Graceful fallback for unknown or generic files."""

    language_name = ProgrammingLanguage.UNKNOWN.value
    extensions = ()
