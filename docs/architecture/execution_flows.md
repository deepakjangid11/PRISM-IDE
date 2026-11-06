# PRISM Execution Sequences & Runtime Workflows

> **Document Version:** 1.0.0  
> **Source Files Referenced:** `src/prism/api/routes/`, `src/prism/intelligence/`, `src/prism/storage/repositories/`  

---

## 1. Developer Activity Ingestion & Working Session Binding

This sequence illustrates what happens when an IDE plugin sends a telemetry event (e.g. file edit, save, or test run) to PRISM:

```mermaid
sequenceDiagram
    autonumber
    participant IDE as IDE / Client Extension
    participant API as Activity Router (/activity/record)
    participant Recorder as ActivityRecorder (developer_activity.py)
    participant SessService as DeveloperSessionService (developer_session.py)
    participant Repo as ActivityRepository (mysql_activity_repo.py)
    participant DB as MySQL Database (developer_activities)

    IDE->>API: POST /activity/record (DeveloperActivity payload)
    API->>Recorder: record(activity)
    
    Recorder->>SessService: get_active_session(activity.developer_id)
    alt Active Session Found & Unexpired
        SessService-->>Recorder: Active DeveloperSession
        Recorder->>SessService: heartbeat(session.session_id)
        Note over Recorder: Sets activity.session_id = session.session_id
    else No Session or Expired
        SessService-->>Recorder: None
        Note over Recorder: Leaves activity.session_id = None
    end

    Recorder->>Repo: save(activity)
    Repo->>DB: INSERT INTO developer_activities (...)
    DB-->>Repo: Success
    Repo-->>Recorder: Saved DeveloperActivity
    Recorder-->>API: ActivityRecordResponse(status="recorded", event_id=...)
    API-->>IDE: HTTP 200 OK (JSON)
```

---

## 2. Skill Evidence Generation & Proficiency Updates

This sequence demonstrates how concrete technical evidence is evaluated to progress a developer's assessed proficiency:

```mermaid
sequenceDiagram
    autonumber
    participant Client as Client / Orchestrator
    participant API as Skills Router (/skills/evidence)
    participant Tracker as SkillTracker (skill_tracker.py)
    participant Graph as SkillGraph (skill_graph.py)
    participant SkillRepo as SkillRepository (mysql_skill_repo.py)
    participant DB as MySQL Database (developer_skills, skill_evidence)

    Client->>API: POST /skills/evidence (SkillEvidence payload)
    API->>Tracker: record_evidence(evidence)
    
    Tracker->>SkillRepo: get_profile(developer_id)
    SkillRepo->>DB: SELECT * FROM developer_skills WHERE developer_id = ...
    DB-->>SkillRepo: Profile Data
    SkillRepo-->>Tracker: DeveloperSkillProfile
    
    Note over Tracker: Appends evidence to skill.evidence_list
    Note over Tracker: Calculates Multi-Factor Score:<br/>Quantity + Strength + Complexity + Diversity + Confidence
    Note over Tracker: Evaluates Milestone Thresholds:<br/>e.g. count >= 6 & has_verified_artifact -> INTERMEDIATE
    
    Tracker->>SkillRepo: save_evidence(evidence)
    SkillRepo->>DB: INSERT INTO skill_evidence (...)
    Tracker->>SkillRepo: save_skill(developer_id, developer_skill)
    SkillRepo->>DB: INSERT / UPDATE INTO developer_skills (...)
    DB-->>SkillRepo: Success
    
    Tracker-->>API: Updated DeveloperSkill
    API-->>Client: HTTP 200 OK (SkillEvidenceResponse)
```

---

## 3. Personalized Task Generation

This sequence details how PRISM scans for competency deficiencies and formulates practice tasks:

```mermaid
sequenceDiagram
    autonumber
    participant Client as Client / IDE
    participant API as Tasks Router (/tasks/generate)
    participant Engine as TaskRecommendationEngine (task_recommendation_engine.py)
    participant Tracker as SkillTracker (skill_tracker.py)
    participant GapAnalyzer as KnowledgeGapAnalyzer (knowledge_gap_analyzer.py)
    participant Graph as SkillGraph (skill_graph.py)
    participant IntelRepo as IntelligenceRepository (mysql_intelligence_repo.py)
    participant DB as MySQL Database (personalized_tasks)

    Client->>API: POST /tasks/generate (developer_id, target_role="Backend Developer")
    API->>Engine: generate_tasks(developer_id, target_role, limit=5)
    
    Engine->>Tracker: get_profile(developer_id)
    Tracker-->>Engine: DeveloperSkillProfile
    
    Engine->>GapAnalyzer: identify_gaps(profile, target="Backend Developer")
    GapAnalyzer->>Graph: get_role_skills("Backend Developer")
    Graph-->>GapAnalyzer: Required Skills list
    GapAnalyzer-->>Engine: list[SkillGap] (missing prerequisites & under-proficient skills)
    
    loop For each actionable gap (not yet mastered)
        Note over Engine: Selects difficulty matching current level:<br/>INSUFFICIENT_DATA -> BEGINNER<br/>BEGINNER -> ELEMENTARY<br/>INTERMEDIATE -> INTERMEDIATE
        Note over Engine: Formulates acceptance criteria, title, time estimate
        Engine->>IntelRepo: save_task(task)
        IntelRepo->>DB: INSERT INTO personalized_tasks (...)
    end
    
    IntelRepo-->>Engine: Tasks saved
    Engine-->>API: list[TaskRecommendation]
    API-->>Client: HTTP 200 OK (list of PersonalizedTask JSON)
```

---

## 4. Task Evaluation & Automated Learning Feedback Loop

This sequence illustrates the **bidirectional feedback loop** where completing a practice task automatically generates verifiable `SkillEvidence`, raises skill proficiency, and recalibrates pedagogical learning strategy:

```mermaid
sequenceDiagram
    autonumber
    participant Developer as Developer / IDE Test Runner
    participant API as Tasks Router (/tasks/{task_id}/evaluate)
    participant TaskEngine as TaskRecommendationEngine (task_recommendation_engine.py)
    participant Tracker as SkillTracker (skill_tracker.py)
    participant AdaptEngine as LearningAdaptationEngine (learning_adaptation_engine.py)
    participant FeedEngine as IntelligentFeedbackEngine (intelligent_feedback_engine.py)
    participant IntelRepo as IntelligenceRepository (mysql_intelligence_repo.py)
    participant DB as MySQL Database (task_outcomes, skill_evidence)

    Developer->>API: POST /tasks/tsk_001/evaluate (passed=true, score=0.9, artifacts=[...])
    API->>TaskEngine: evaluate_task_completion(task_id, success=True, execution_notes, artifacts)
    
    TaskEngine->>IntelRepo: get_task("tsk_001")
    IntelRepo-->>TaskEngine: PersonalizedTask
    
    Note over TaskEngine: Computes TaskEvaluation score & strengths
    TaskEngine->>IntelRepo: save_task_outcome(outcome)
    IntelRepo->>DB: INSERT INTO task_outcomes (...)
    
    opt When Task Passed (success == True)
        Note over TaskEngine: AUTOMATED EVIDENCE FEEDBACK LOOP:<br/>Creates SkillEvidence(source='task_execution', strength=1.8)
        TaskEngine->>Tracker: record_evidence(new_evidence)
        Note over Tracker: Re-evaluates proficiency score & advances level
        Tracker->>DB: Persists updated skill level & evidence
        
        Note over TaskEngine: Updates task.status = 'COMPLETED'
        TaskEngine->>IntelRepo: save_task(updated_task)
    end
    
    TaskEngine-->>API: TaskEvaluation report
    
    par Async Recalibration & Feedback
        API->>AdaptEngine: adapt_strategy(developer_id)
        AdaptEngine->>DB: Queries recent task success rates & adapts strategy
        API->>FeedEngine: generate_feedback_for_task(developer_id, task, outcome)
        FeedEngine->>DB: Inserts constructive praise & next steps into developer_feedbacks
    end
    
    API-->>Developer: HTTP 200 OK (TaskEvaluation JSON)
```

---

## 5. Adaptive Mentoring Request

This sequence shows how mentoring queries are intercepted, mapped to dynamic teaching strategies, and customized based on the developer's experience and active gaps:

```mermaid
sequenceDiagram
    autonumber
    participant Dev as Developer / Chat Interface
    participant API as Mentoring Router (/mentoring/adaptive)
    participant Mentor as AdaptiveMentoringEngine (adaptive_engine.py)
    participant IntelEngine as DeveloperIntelligenceEngine (developer_intelligence_engine.py)
    participant TaskEngine as TaskRecommendationEngine (task_recommendation_engine.py)
    participant BaseMentor as MentoringEngine (engine.py)
    participant IntelRepo as IntelligenceRepository (mysql_intelligence_repo.py)
    participant DB as MySQL Database (mentoring_sessions)

    Dev->>API: POST /mentoring/adaptive (query="Why does my query fail?", target_skill="SQL")
    API->>Mentor: request_adaptive_mentoring(request)
    
    Mentor->>IntelEngine: get_profile(developer_id)
    IntelEngine-->>Mentor: DeveloperIntelligenceProfile (trends, active_gaps)
    
    Note over Mentor: Strategy Selection Logic:<br/>Query has 'fail/error' -> DEBUGGING_GUIDANCE<br/>Target skill in active_gaps -> STEP_BY_STEP_LEARNING<br/>Target skill proficient -> ADVANCED_TECHNICAL_GUIDANCE
    
    Note over Mentor: Calibrates complexity:<br/>foundational vs targeted vs advanced
    
    Mentor->>BaseMentor: request_mentoring(base_request)
    BaseMentor-->>Mentor: Base explanation & code templates
    
    Mentor->>TaskEngine: get_tasks(developer_id, status="GENERATED")
    TaskEngine-->>Mentor: Available practice tasks
    Note over Mentor: Attaches suggested practice task to response
    
    Mentor->>IntelRepo: save_mentoring_session(session_record)
    IntelRepo->>DB: INSERT INTO mentoring_sessions (...)
    
    Mentor-->>API: AdaptiveMentorResponse
    API-->>Dev: HTTP 200 OK (Tailored Guidance, Steps, & Practice Task)
```

---

## 6. End-to-End Intelligence Orchestration

This sequence demonstrates the central role of `CrossModuleIntelligenceOrchestrator` when reacting to an incoming telemetry event:

```mermaid
sequenceDiagram
    autonumber
    participant IDE as IDE Plugin
    participant API as Intelligence Router (/intelligence/orchestrate/activity)
    participant Orch as CrossModuleIntelligenceOrchestrator (intelligence_orchestrator.py)
    participant Sess as DeveloperSessionService
    participant EvidenceEng as SkillEvidenceEngine
    participant Tracker as SkillTracker
    participant IntelEng as DeveloperIntelligenceEngine
    participant FeedEng as IntelligentFeedbackEngine
    participant IntelRepo as IntelligenceRepository

    IDE->>API: POST /intelligence/orchestrate/activity (DeveloperActivity)
    API->>Orch: process_activity_and_recalibrate(activity)
    
    Orch->>Sess: get_active_session(activity.developer_id)
    Sess-->>Orch: Active session status
    
    Orch->>EvidenceEng: extract_and_record(activity)
    opt If Activity Contains Verifiable Code Artifact / Test
        EvidenceEng->>Tracker: record_evidence(evidence)
        Tracker-->>Orch: Evidence recorded
    end
    
    Orch->>IntelEng: analyze_developer(activity.developer_id)
    IntelEng->>IntelRepo: Recalculates trends, detects error spikes, saves insights
    IntelEng-->>Orch: IntelligenceAnalysisResult
    
    opt If Error Telemetry Detected (syntax_error or runtime_error)
        Orch->>FeedEng: generate_proactive_feedback(activity.developer_id)
        FeedEng->>IntelRepo: Saves corrective guidance into developer_feedbacks
    end
    
    Orch-->>API: dict(status="success", evidence_id=...)
    API-->>IDE: HTTP 200 OK
```

---

## 7. MySQL Persistence & Transactional Boundary Flow

This sequence demonstrates PRISM's transactional boundaries, connection pooling, and error handling in `MySQLIntelligenceRepository`:

```mermaid
sequenceDiagram
    autonumber
    participant Engine as Any Domain Engine (e.g. TaskRecommendationEngine)
    participant Repo as MySQLIntelligenceRepository (mysql_intelligence_repo.py)
    participant Pool as SQLAlchemy Engine & ConnectionPool (database.py)
    participant DB as MySQL 8.0 Server

    Engine->>Repo: save_task(PersonalizedTask)
    Note over Repo: Enters context manager: with self._get_session() as session:
    
    Repo->>Pool: session_factory() Checkout Connection
    Pool->>DB: START TRANSACTION;
    
    Repo->>DB: SELECT * FROM personalized_tasks WHERE task_id = 'tsk_001';
    alt Task Exists (Update)
        Repo->>DB: UPDATE personalized_tasks SET status = ..., notes = ... WHERE task_id = 'tsk_001';
    else Task New (Insert)
        Repo->>DB: INSERT INTO personalized_tasks (task_id, developer_id, ...) VALUES (...);
    end
    
    alt Operation Succeeds
        Repo->>DB: COMMIT;
        Pool-->>Repo: Connection recycled to pool
        Repo-->>Engine: Return None (Success)
    else Exception Raised (e.g. FK Violation, Deadlock)
        Repo->>DB: ROLLBACK;
        Pool-->>Repo: Connection reset and returned to pool
        Repo-->>Engine: Re-raises Exception / Logged Error
    end
```
