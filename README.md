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

### 5. Multi-Language Developer Activity Intelligence (Phase 17)
- **Extensible Adapters**: Pluggable language adapters for Python, Java, C#, TypeScript, JavaScript, Go, Rust, C, C++, PHP, Ruby, Kotlin, Swift, Dart, SQL, HTML, CSS.
- **`ActivityClassifier`**: Multi-dimensional activity classification categorizing development actions into backend, frontend, database, DevOps, testing, systems, and mobile.
- **`ActivityAggregationEngine`**: Real-time aggregation of coding activities into language distributions, framework usage, and session velocities.

### 6. Advanced Skill Graph, Evidence Intelligence & Skill Gap Detection (Phase 18)
- **`SkillEvidenceEngine`**: Continuous ingestion of developer activities into verifiable `SkillEvidence` artifacts with SHA256 deduplication, event weighting, implementation complexity estimation, and filtering of non-evidential events.
- **Advanced `SkillGraph`**: Rich `SkillNode` registry supporting multi-language metadata, category/language filtering, career role competencies (e.g. Machine Learning Engineer, Backend Developer, Full Stack Developer, Frontend Developer, Mobile Developer), and cycle-safe directed topological traversal.
- **Proficiency Intelligence (`SkillTracker`)**: Multi-factor scoring model assessing quantity (with diminishing returns), evidence quality/strength, complexity, project diversity, and observation confidence across `insufficient_data`, `beginner`, `elementary`, `intermediate`, `advanced`, and `expert` with human-readable diagnostic explanations.
- **`KnowledgeGapAnalyzer`**: Multi-path gap detection identifying missing prerequisites and under-proficient competencies against target technical skills and career roles.
- **`LearningRecommendationEngine`**: Generates prioritized recommendations (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) with target proficiency goals, difficulty levels, and realistic effort estimations.
- **`LearningPathGenerator`**: Dependency-aware topological roadmap synthesis skipping acquired prerequisites and calculating effort hours.
- **MySQL Persistence**: Full storage integration into MySQL 8.0+ via SQLAlchemy 2.0 with zero SQLite dependencies, preserving evidence metadata and multidimensional developer skill profiles.

---

## API Endpoints

FastAPI endpoints are exposed under modular routers:

- **Project Intelligence**:
  - `POST /projects/analyze`: Analyze project files and syntax.
  - `POST /projects/intelligence`: Generate full structural, dependency, and relationship intelligence.
- **Developer Identity & Working Sessions (Phase 16)**:
  - `POST /developer/register`: Register new developer identity.
  - `POST /developer/identify`: Resolve developer identity.
  - `POST /developer/session/start`: Start active working session.
  - `POST /developer/session/heartbeat`: Touch session activity heartbeat.
  - `POST /developer/session/end`: Terminate active working session.
  - `GET /developer/session/active/{developer_id}`: Retrieve current active session.
  - `GET /developer/session/history/{developer_id}`: Paginated working session history.
- **Multi-Language Developer Activity Intelligence (Phase 17)**:
  - `POST /activity/record`: Ingest developer activity event.
  - `POST /activity/classify`: Classify source code activity across languages.
  - `GET /activity/developer/{developer_id}`: Retrieve developer activity stream.
  - `GET /activity/summary/{developer_id}`: Multi-language activity intelligence summary.
- **Advanced Skills & Intelligence (Phase 18)**:
  - `GET /skills/profile/{developer_id}`: Retrieve multidimensional skill profile with rollups.
  - `POST /skills/evidence`: Record verifiable skill evidence and trigger proficiency evaluation.
  - `GET /skills/evidence/{developer_id}`: Chronological skill evidence records with filtering.
  - `GET /skills/proficiency/{developer_id}`: Complete assessed skill competencies map.
  - `GET /skills/proficiency/{developer_id}/{skill_id}`: Assessed proficiency and explainability reasoning for a single skill.
  - `GET /skills/graph`: Full or filtered (category, language) skill graph topology snapshot.
  - `GET /skills/graph/{skill_id}`: Detailed `SkillNode` metadata.
  - `GET /skills/prerequisites/{skill_id}`: Direct or transitive prerequisite skills.
  - `GET /skills/related/{skill_id}`: Related adjacent technical concepts.
  - `POST /skills/gap-analysis`: Analyze competency gaps for target skill or career role.
  - `GET /skills/gaps/{developer_id}`: Query detected gaps for developer.
  - `GET /skills/recommendations/{developer_id}`: Prioritized, effort-estimated learning recommendations.
  - `POST /skills/learning-path`: Generate dependency-aware topological learning path.
  - `GET /skills/learning-path/{developer_id}`: Query tailored learning path for skill or role.
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
