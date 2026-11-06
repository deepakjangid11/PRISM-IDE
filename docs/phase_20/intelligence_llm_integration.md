# PRISM IDE — Phase 20 Intelligence + LLM Integration

## 1. Overview

In PRISM, the Large Language Model does NOT replace existing intelligence modules — it serves as the **pedagogical reasoning and explanation synthesis layer**. 

Rather than sending raw code directly to an LLM, PRISM compiles a rich, structured developer dossier from verified database telemetry:
1. **Developer Profile:** Overall status, verified core strengths, active knowledge gaps, competency velocity.
2. **Skill Competency Evidence:** Verified proficiency scores, evidence counts, assessment reasoning, and missing prerequisites from the Skill Graph.
3. **Execution & Error Telemetry:** Recurring errors, severity levels, and past debugging friction.
4. **Task Context:** Active practice tasks and recommended challenges.
5. **Project Context & RAG Citations:** Relevant code fragments with exact line citations.

---

## 2. Pedagogical Strategy Alignment

The LLM system prompt is dynamically calibrated based on PRISM's `MentoringStrategy` enum:

| Mentoring Strategy | Pedagogical Focus | Guidance Style |
| :--- | :--- | :--- |
| `CONCEPTUAL_EXPLANATION` | Foundational principles & mental models | High clarity, analogies, avoids overwhelming syntax |
| `GUIDED_IMPLEMENTATION` | Step-by-step walkthrough | Idiomatic design patterns, modular code blueprints |
| `STEP_BY_STEP_LEARNING` | Milestone-based progression | Sequential steps, validates prerequisite mastery |
| `DEBUGGING_GUIDANCE` | Root-cause isolation | Systematic verification, reproduction tests, edge cases |
| `PRACTICAL_EXERCISE` | Hands-on challenge | Interactive coding challenge with acceptance criteria |
| `ADVANCED_TECHNICAL_GUIDANCE` | Architecture & scale | Concurrency, memory footprint, throughput, resiliency |

---

## 3. Context Construction Pipeline

```mermaid
flowchart LR
    DevID["Developer ID"] --> ProfileCtx["Profile Context (< 1200 chars)"]
    SkillTracker["Skill Tracker"] --> SkillCtx["Skill Context (< 1000 chars)"]
    ErrorTracker["Error Telemetry"] --> ErrorCtx["Error Telemetry (< 800 chars)"]
    TaskEngine["Task Engine"] --> TaskCtx["Task Context (< 600 chars)"]
    RAGService["RAG Service"] --> RAGCtx["RAG Citations (< 1500 chars)"]

    ProfileCtx --> Assembler["LLMContextBuilder"]
    SkillCtx --> Assembler
    ErrorCtx --> Assembler
    TaskCtx --> Assembler
    RAGCtx --> Assembler

    Assembler --> Scrubber["scrub_sensitive_data() (Regex Privacy Filter)"]
    Scrubber --> Messages["list[LLMMessage] (System + User Prompt)"]
```

---

## 4. Sensitive Data Protection

To guarantee that proprietary developer secrets, API credentials, and internal connection strings are never leaked to external LLM providers, PRISM enforces strict automated sanitization via `scrub_sensitive_data()`:
- **API Keys:** Redacts OpenAI (`sk-...`), Groq (`gsk_...`), and Gemini (`AIzaSy...`) keys to `[REDACTED_API_KEY]`.
- **Database Connection Strings:** Sanitizes credentials in database connection URLs (`mysql://user:pass@host/db`) to `[REDACTED_DB_URL]`.
- **Authorization Tokens:** Sanitizes `Bearer <token>` to `Bearer [REDACTED_BEARER_TOKEN]`.
- **Private Keys:** Strips RSA/DSA/EC private key blocks to `[REDACTED_PRIVATE_KEY]`.
- **Generic Key-Value Secrets:** Replaces `(password|token|secret): <value>` with `\1: [REDACTED]`.
