# PRISM IDE

PRISM IDE is an AI-powered developer intelligence and learning platform backend built with Python 3.14, FastAPI, and Pydantic. It extracts project intelligence from source code, records and evaluates developer behavior streams, tracks verified technical skills through a directed skill graph, generates personalized learning paths, and powers a multi-modal mentoring engine.

---

## Architecture & Data Flow

PRISM operates through an interconnected intelligence pipeline:

```
Source Code / AST
      │
      ▼
Project Intelligence (Context, AST, Code Relationships, Dependencies)
      │
Developer Activity Stream ──► ActivityRecorder ──► ActivityAggregator ──► ActivitySessionAnalyzer
                                                                                  │
                                                                                  ▼
                                                                     DeveloperBehaviorAnalyzer
                                                                                  │
Project Evidence + AST Artifacts ──► SkillAnalyzer ──► SkillTracker ◄─────────────┘
                                                             │
                                                             ▼
                                                    SkillGraph (Prerequisites & Graph Topology)
                                                             │
                                                             ▼
                                                    KnowledgeGapAnalyzer
                                                             │
                                                             ▼
                                                   LearningPathGenerator & RecommendationEngine
                                                             │
                                                             ▼
                                                      MentoringEngine
                                               ┌─────────────┴─────────────┐
                                               ▼                           ▼
                                           Build Mode                  Learn Mode
```

---

## Core Capabilities

### 1. Developer Behavior Intelligence (Phase 10B)
- **`DeveloperBehaviorAnalyzer`**: Evaluates activity streams and session metrics to uncover genuine working patterns without relying on arbitrary event-count thresholds.
- **Key Metrics Analyzed**:
  - Testing habits: testing frequency, test failure rate, test success rate, test-to-edit ratio.
  - Error and assistance rates: runtime/syntax error rates, frequency of AI help utilization.
  - Context exploration: file switching frequency and unique touched files.
  - Session characteristics: active duration distribution, sustained vs. burst sessions.
- **`DeveloperBehaviorInsights`**: Strongly typed model encapsulating behavior metrics, activity distribution, and pattern indicators (e.g. test-driven development, elevated failure rates, focused vs. broad exploration).

### 2. Skill Tracking & Skill Graph (Phase 11)
- **Evidence-Grounded Skills**: Technical proficiency is evaluated strictly through concrete, verifiable artifacts (`SkillEvidence`), such as code artifacts, test passes, and project features, rather than superficial activity counts.
- **`SkillTracker`**: Multi-developer in-memory registry evaluating developer skills (`DeveloperSkill`) and profiles (`DeveloperSkillProfile`). Progresses deterministically from `insufficient_data` to `beginner`, `intermediate`, and `advanced` based on evidence depth, diversity, and multi-project verification.
- **`SkillGraph`**: In-memory directed acyclic graph capturing technical relationships (`prerequisite`, `related`, `specialization_of`) with topological ordering and circular prerequisite prevention.
- **`SkillAnalyzer`**: Automatically discovers observable skill evidence from Python source files, classes, and framework dependencies (e.g., FastAPI, Pydantic, pytest).

### 3. Learning Intelligence (Phase 12)
- **`KnowledgeGapAnalyzer`**: Compares a developer's verified skill profile against the skill graph to identify missing prerequisites, insufficient evidence, or proficiency gaps for any target skill.
- **`LearningRecommendationEngine`**: Generates structured, prioritized, and deduplicated recommendations (`LearningRecommendation`) focusing on high-severity prerequisites first.
- **`LearningPathGenerator`**: Constructs ordered learning paths (`LearningPath`) ensuring prerequisite skills precede dependent skills using topological sorting.
- **`LearningProgressTracker`**: Evaluates completed, in-progress, and remaining skills on any active learning path (`LearningProgress`).

### 4. Mentoring Engine (Phase 13)
- **`MentoringEngine` & `MentorContextBuilder`**: Compiles multi-dimensional intelligence (project structure, developer behavior telemetry, skill profile, and knowledge gaps) to deliver contextual mentoring responses.
- **Two Operational Modes**:
  - **Build Mode**: Mentoring focused on project architecture, code relationships, external dependency audits, unparseable files, and test stability.
  - **Learn Mode**: Concept explanation, prerequisite gap remediation, and structured step-by-step learning roadmaps.
- **Provider-Ready Extensibility**: Uses `BaseMentorGenerator` protocol and `DeterministicMentorGenerator` default implementation, enabling clean future integration with external LLM providers (Groq, OpenAI, Gemini) without architectural refactoring.

---

## API Endpoints

FastAPI endpoints are exposed under modular routers:

- **Project Intelligence**:
  - `POST /projects/analyze`: Analyze project files and syntax.
  - `POST /projects/intelligence`: Generate full structural, dependency, and relationship intelligence.
- **Developer Behavior & Skills**:
  - `POST /developer/behavior`: Analyze developer behavior patterns.
  - `POST /developer/skills/record`: Record concrete skill evidence.
  - `GET /developer/skills/{developer_id}`: Retrieve developer skill profile.
  - `GET /developer/skills/graph`: Export the full skill graph.
- **Learning Intelligence**:
  - `POST /learning/gaps`: Identify missing skill prerequisites.
  - `POST /learning/paths`: Generate structured learning path.
  - `POST /learning/recommendations`: Retrieve prioritized learning recommendations.
- **Mentoring**:
  - `POST /mentoring/request`: Submit mentoring request in Build or Learn Mode.
- **Health**:
  - `GET /health`: System health and service metadata.

---

## Running Quality Verification & Tests

PRISM uses `uv` for dependency management, Ruff for linting and formatting, MyPy for static type checking, and pytest for testing.

### 1. Run Linting
```powershell
uv run ruff check .
```

### 2. Check Formatting
```powershell
uv run ruff format --check .
```

### 3. Run Static Type Checking
```powershell
uv run mypy src
```

### 4. Execute Full Test Suite
```powershell
uv run pytest -v
```

### 5. Run Test Coverage
```powershell
uv run pytest --cov=prism --cov-report=term-missing
```
