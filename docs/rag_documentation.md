# PRISM — RAG Architecture & Code Intelligence Documentation

**Module:** `src/prism/rag/`
**Purpose:** Retrieval-Augmented Generation for Project Code Intelligence and Mentoring Grounding
**Embedding Dimension:** 128 (Deterministic) / 1536 (Remote)
**Persistence Format:** JSON Atomic Storage (`.prism/rag_store.json`)

---

## 1. End-to-End RAG Pipeline

PRISM implements a full 9-stage RAG pipeline designed for zero-crash offline execution and optional high-dimensional remote embedding APIs.

```
+------------------+
| Source Documents |  (Python, Markdown, TypeScript, SQL, YAML)
+--------+---------+
         |
         v
+------------------+
| Document Loading |  (Reads file content, extracts encoding, validates paths)
+--------+---------+
         |
         v
+------------------+
|     Chunking     |  (AST Function/Class Splitter for .py; Sliding Window for others)
+--------+---------+
         |
         v
+------------------+
|    Embedding     |  (Deterministic Token MD5 & 3-gram sign hashing; normalized L2)
+--------+---------+
         |
         v
+------------------+
|   Vector Store   |  (Thread-safe in-memory index; atomic JSON persistence)
+--------+---------+
         |
         v
+------------------+
|    Retrieval     |  (Cosine similarity calculation, top-k ranking, min-score threshold)
+--------+---------+
         |
         v
+------------------+
| Context Building |  (Safe citation blocks: [Source: file.py:start-end])
+--------+---------+
         |
         v
+------------------+
|  LLM Generation  |  (Context injected into LLM Request system prompt)
+--------+---------+
         |
         v
+------------------+
| Grounded Output  |  (Socratic mentoring response with verifiable source references)
+------------------+
```

---

## 2. Chunking Strategy

### 2.1 Python AST Chunking (`CodeDocumentChunker`)
- **Engine:** Python standard library `ast`.
- **Logic:** Walks top-level and nested AST nodes to extract discrete semantic boundaries:
  - `ast.FunctionDef` / `ast.AsyncFunctionDef`
  - `ast.ClassDef`
- **Metadata Preserved:**
  - `chunk_id`: SHA-256 hash of `file_path:start_line-end_line`.
  - `symbol_name`: Function or class identifier.
  - `start_line` / `end_line`: 1-based source line numbers.
  - `language`: `"python"`.

### 2.2 Fallback Sliding Window Chunking
- **Application:** Non-Python files (`.md`, `.ts`, `.json`, `.sql`) or Python files with syntax errors.
- **Window Size:** 500 characters.
- **Window Overlap:** 100 characters.

---

## 3. Embedding Generation

### 3.1 Deterministic Embedding Provider (`DeterministicEmbeddingProvider`)
- **Dimensionality:** 128 dimensions.
- **Methodology:**
  1. Tokenizes text via regex `\w+`.
  2. Projects each token into 128 dimensional buckets using MD5 hash modulo.
  3. Applies sign hashing (`(h >> 8) % 2 == 0 ? +1.0 : -1.0`) to avoid bucket bias.
  4. Generates 3-gram character sub-word hashes for identifier prefix/suffix representation.
  5. Normalizes vector to unit L2 norm: $\vec{v}_{norm} = \frac{\vec{v}}{\|\vec{v}\|_2}$.
- **Advantages:** 100% offline, zero C-compiler dependencies, 100% deterministic across operating systems.

### 3.2 Remote Embedding Provider (`RemoteEmbeddingProvider`)
- **API Endpoint:** OpenAI-compatible embedding API (`https://api.openai.com/v1/embeddings`).
- **Model:** `text-embedding-3-small` (1536 dimensions).
- **Graceful Fallback:** If API credentials are missing or the network fails, automatically falls back to the deterministic provider without interrupting user queries.

---

## 4. Vector Storage & Semantic Search

### 4.1 Cosine Similarity Formulation
Given query vector $\vec{q}$ and chunk vector $\vec{c}$:
$$\text{Sim}(\vec{q}, \vec{c}) = \frac{\vec{q} \cdot \vec{c}}{\|\vec{q}\|_2 \|\vec{c}\|_2}$$

### 4.2 Filtering & Deletion Capabilities
- **Project Path Filter:** Restricts search to a specific workspace directory.
- **Language Filter:** Restricts candidates to target programming language.
- **Similarity Threshold:** Discards candidates scoring below `min_score` (default 0.0 - 0.2).
- **Document Update / Deletion:** `delete_file(file_path)` purges existing chunks prior to re-indexing to prevent duplicate chunks.
- **Persistence:** Atomic write via `.tmp` file swap to `.prism/rag_store.json`.
