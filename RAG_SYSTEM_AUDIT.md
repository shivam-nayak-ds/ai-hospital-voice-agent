# 🏥 ASHA RAG & Voice Agent: Production Architecture Audit & 15-Phase Deployment Roadmap
**Date:** June 2, 2026 | **Version:** 4.0 (Enterprise Production Spec)

This document provides a comprehensive technical audit of the **ASHA Hospital Voice & Web Agent** and outlines a detailed **15-Phase Implementation Roadmap** to build, evaluate, and deploy the system in production.

---

## 🏗️ Production Architecture Diagram

The sequence below guarantees sub-500ms voice latencies while maintaining clinical precision through hybrid retrieval, cross-encoder reranking, and proactive sentence tokenization.

```text
                    USER (Voice / Web App)
                              │  ▲
               Bidirectional  │  │  Audio Stream (24kHz / Mulaw)
                 WebSockets   ▼  │
                       ┌───────────┐
                       │  FastAPI  │
                       └─────┬─────┘
                             │
                             ▼
                  LangGraph Orchestrator
                             │
       ┌─────────────────────┼──────────────────────┐
       ▼                     ▼                      ▼
  Redis Memory          Safety Guardrail       Intent Router
 (Session Cache)         (Rules + LLM)          (Tool Select)
                                                    │
    ┌───────────────────────────────────────────────┼────────────────────────┐
    ▼                                               ▼                        ▼
FAQ Tool                                     Doctor Search Tool       Appointment Tool
    │                                               │
    └───────────────────────┬───────────────────────┘
                            ▼
                         RAG Tool
                            │
                    Metadata Filtering
                (department, clinic, type)
                            │
               ┌────────────┴────────────┐
               ▼                         ▼
          BM25 Search              Qdrant Search
       (Sparse Retrieval)        (Dense Retrieval)
               └────────────┬────────────┘
                            ▼
                    RRF Hybrid Fusion
                            ▼
                  Cross Encoder Reranker
                            ▼
                     Citation Builder
                            ▼
                     Context Builder
                            ▼
                   GPT-4o-mini / Groq
                            ▼
                    Response Streaming
                            ▼
                    Sentence Splitter
                            ▼
                       TTS Engine
                     (Azure / Edge)
                            ▼
                           USER
```

---

## 🚦 System Component Audit

This table summarizes the status of the current implementation and maps out the production requirements and target SLAs.

| Architecture Component | Status | Current Implementation | Production Target Tech Stack | Latency / SLA Target |
| :--- | :--- | :--- | :--- | :--- |
| **Ingestion Pipeline** | 🛠️ *Draft* | Single standard `Document` class; loaders are empty stubs. | Multi-format parser (PyPDF, JSON, MD) with schema validation. | < 5s per document |
| **Dense Vector Store** | ❌ *Pending* | Legacy code uses ChromaDB. | Qdrant client connection pool with HNSW indexing. | < 30ms query latency |
| **Sparse Indexing** | ❌ *Pending* | None. | `rank-bm25` serialized via SQLite or compressed JSON. | < 10ms query latency |
| **Metadata Filtering** | ❌ *Pending* | None. | Vector payload pre-filtering + BM25 corpus matching. | < 5ms processing time |
| **Hybrid Fusion** | ❌ *Pending* | None. | Reciprocal Rank Fusion (RRF) algorithm (Constant $k=60$). | < 5ms processing time |
| **Reranking** | ❌ *Pending* | None. | `SentenceTransformers` with `BAAI/bge-reranker-base`. | < 120ms execution time |
| **Agent Orchestrator** | 🛠️ *Draft* | Basic async loop with simple state logic. | LangGraph state graph + Redis-backed multi-user cache. | < 150ms routing time |
| **Safety Guardrails** | ❌ *Pending* | None. | Guardrail manager (Regex + prompt-based classification). | < 80ms filter time |
| **LLM Inference** | 🛠️ *Draft* | Single sync client calls. | `AsyncOpenAI` + Groq client pool with circuit-breaker failovers. | < 250ms TTFT |
| **Audio Processing** | ✅ *Done* | PyAudio STT and Edge TTS/Azure TTS integrations. | Bidirectional FastAPI WebSockets + background prefetch queue. | Sub-500ms loop response |

---

## 🚀 15-Phase Implementation Roadmap

---

### 📌 Phase 1: Environment & Config System Configuration
*   **Objective**: Establish a unified, type-safe settings engine to manage credentials and application params across all services.
*   **Target Files**:
    *   [config/settings.py](file:///d:/AI-Hospital-Agent/config/settings.py): Extend to validate Qdrant, Redis, PostgreSQL, and LLM providers.
    *   `scripts/boot_check.py`: Checks all connectivity and settings before booting.
*   **Technical Design**:
    *   Leverage Pydantic `BaseSettings` to read `.env` with strict types and default fallbacks.
    *   Implement checking functions to ping Redis, Qdrant, PostgreSQL, and check LLM key validity.
*   **Tasks**:
    *   Configure settings schema with all environment variables.
    *   Create boot check script to ping connection endpoints.
    *   Hook boot verification to container start commands.
*   **Verification Plan**:
    *   Run boot script with invalid environment credentials to verify startup is blocked.
    *   Test standard success response with active docker infrastructure services.
*   **Deliverable**: A boot validation script that blocks the main process from starting if vital services are unreachable.

---

### 📌 Phase 2: RAG Data Ingestion & Unified Document Model
*   **Objective**: Standardize doc reading by compiling varied source data (FAQ JSON, Markdown rules, handbook PDFs) into a single `Document` structure.
*   **Target Files**:
    *   [src/rag/loaders/documents.py](file:///d:/AI-Hospital-Agent/src/rag/loaders/documents.py): Contains the standard `Document` dataclass.
    *   [src/rag/loaders/json_loader.py](file:///d:/AI-Hospital-Agent/src/rag/loaders/json_loader.py): Parses structured doctors, clinics, and FAQ lists.
    *   [src/rag/loaders/markdown_loader.py](file:///d:/AI-Hospital-Agent/src/rag/loaders/markdown_loader.py): Parses operational notes and markdown policies.
    *   [src/rag/loaders/pdf_loader.py](file:///d:/AI-Hospital-Agent/src/rag/loaders/pdf_loader.py): Extracts handbook guidelines.
*   **Technical Design**:
    *   Every loader must implement an interface: `load(self) -> list[Document]`.
    *   Metadata dicts must follow strict type rules: `source`, `category`, `clinic_id`, `department_id`, and `type`.
*   **Tasks**:
    *   Implement `JSONLoader` to load list of structured FAQs.
    *   Implement `MarkdownLoader` to parse structural policy layouts.
    *   Implement `PDFLoader` to read binary tables and pages from PDFs.
*   **Verification Plan**:
    *   Write a unit test reading `config/knowledge_base.json` using `JSONLoader`.
    *   Assert that returned documents have non-empty `page_content` and valid metadata keys.
*   **Deliverable**: Python parser classes returning standardized `Document` objects from PDF, JSON, and MD files.

---

### 📌 Phase 3: Text Splitting & Metadata Enrichment
*   **Objective**: Slice long documents into semantically coherent text chunks with appropriate overlaps and inject parent metadata.
*   **Target Files**:
    *   `src/rag/processing/chunking.py`: Handles recursive character-based semantic splitting.
*   **Technical Design**:
    *   Use `RecursiveCharacterTextSplitter` from langchain-text-splitters.
    *   Chunk Size: 400 tokens; Overlap: 50 tokens (using `tiktoken` encoder representation).
    *   Tag chunks with unique `chunk_id` consisting of `doc_hash:index` to support citation mappings.
*   **Tasks**:
    *   Build splitting configurations mapping token boundaries.
    *   Construct metadata tagging pipeline merging document parent details with segment offsets.
*   **Verification Plan**:
    *   Pass a 10,000-character test string through `SemanticChunker`.
    *   Assert chunk sizes remain below constraints and overlap sequences are intact.
*   **Deliverable**: Chunker module generating bounded text segments with inherited metadata.

---

### 📌 Phase 4: Dense Vector Storage (Qdrant Integration)
*   **Objective**: Initialize Qdrant database collections, generate dense embeddings, and load documents.
*   **Target Files**:
    *   [src/rag/vectorstore/qdrant_manager.py](file:///d:/AI-Hospital-Agent/src/rag/vectorstore/qdrant_manager.py): Connection pooling and collections manager.
    *   `src/rag/embeddings/embedding_model.py`: Local vector builder setup using `sentence-transformers`.
*   **Technical Design**:
    *   Primary Model: `BAAI/bge-large-en-v1.5` or `all-MiniLM-L6-v2` (1024 / 384 dimensions).
    *   Metric: Cosine. Configure payload indexing on `clinic_id`, `department_id`, and `type`.
*   **Tasks**:
    *   Define Qdrant connection management and setup target collection models.
    *   Initialize Hugging Face embedding pipeline to generate dense vectors.
    *   Write batch upsert functions using qdrant client interfaces.
*   **Verification Plan**:
    *   Recreate collections and perform upsert operations.
    *   Perform a cosine-similarity retrieval scan and verify response payload structure.
*   **Deliverable**: Ingestion driver script inserting vector payloads into Qdrant.

---

### 📌 Phase 5: Sparse Retrieval Engine (BM25 Setup)
*   **Objective**: Configure keyword search to retrieve exact medical nomenclature, department codes, and doctor names.
*   **Target Files**:
    *   [src/rag/retrieval/bm25_search.py](file:///d:/AI-Hospital-Agent/src/rag/retrieval/bm25_search.py): Core keyword indexing algorithm.
*   **Technical Design**:
    *   Implement tokenization filtering out common Hindi and English stop words.
    *   Serialize tokenized document mappings to SQLite or compact JSON for quick load-up.
*   **Tasks**:
    *   Construct corpus tokenizer processing queries and documents.
    *   Build rank-bm25 index loader saving data models locally.
    *   Expose lookup query function return top-k matches with raw scoring metrics.
*   **Verification Plan**:
    *   Query for exact terms like "CBC" or "Dr. Rajesh Sharma" on a custom populated dataset.
    *   Verify match accuracy surpasses dense vector scores for keyword-sensitive queries.
*   **Deliverable**: Tokenizer and index builder generating a queryable BM25 pickle payload.

---

### 📌 Phase 6: Metadata Pre-Filtering
*   **Objective**: Restrict both retrieval indexes (dense/sparse) to target departments, clinics, or document types.
*   **Target Files**:
    *   `src/rag/retrieval/vector_search.py`: Vector lookup implementation.
    *   [src/rag/retrieval/bm25_search.py](file:///d:/AI-Hospital-Agent/src/rag/retrieval/bm25_search.py): Augmented sparse search.
*   **Technical Design**:
    *   Construct Qdrant search filters dynamically via nested `FieldCondition` match objects.
    *   Apply matching filtering loops to BM25 candidate list scans.
*   **Tasks**:
    *   Write dynamic filter translators mapping key-value arguments to database specifications.
    *   Combine filtering criteria check step to sparse indexing search workflows.
*   **Verification Plan**:
    *   Run test assertions verifying queries specifying `clinic_id="cardio_clinic"` never return general ward document records.
*   **Deliverable**: Filter constructor middleware integrated into sparse/dense retrieval flows.

---

### 📌 Phase 7: Reciprocal Rank Fusion (RRF) Hybrid Fusion
*   **Objective**: Combine dense vector proximity scores and sparse term frequencies using the RRF rank-merging algorithm.
*   **Target Files**:
    *   `src/rag/retrieval/hybrid_search.py`: Merges outputs from both search pipelines.
*   **Technical Design**:
    *   Mathematical ranking equation:
        $$RRF\_Score(d \in D) = \sum_{m \in M} \frac{1}{k + r_m(d)}$$
    *   Set constant $k=60$ to balance high/low rankings.
*   **Tasks**:
    *   Write mathematical rank score merging parser sorting candidates based on position ratios.
    *   De-duplicate overlapping records between indexes.
*   **Verification Plan**:
    *   Feed overlapping mock rankings to RRF utility. Verify math output checks out.
*   **Deliverable**: Hybrid Search runner mapping multi-index outputs to a unified list.

---

### 📌 Phase 8: Cross-Encoder Reranking
*   **Objective**: Perform deeper context scoring of hybrid-retrieved documents via cross-attention models to select top-3 chunks.
*   **Target Files**:
    *   `src/rag/retrieval/reranker.py`: Loads cross-encoder weights and runs evaluations.
*   **Technical Design**:
    *   Model: `BAAI/bge-reranker-base` via PyTorch / HuggingFace.
    *   Filter out chunks dropping below similarity thresholds (e.g. relevance < 0.35).
*   **Tasks**:
    *   Setup CrossEncoder models mapping query-document text segments.
    *   Sort and drop chunks dropping below quality threshold configuration limits.
*   **Verification Plan**:
    *   Assert irrelevant context items (inserted artificially) get weeded out.
*   **Deliverable**: Rerank wrapper outputting highly relevant chunks.

---

### 📌 Phase 9: Citation & Context Builder
*   **Objective**: Format prompt inserts, attaching structured, dynamic index citations to all context blocks.
*   **Target Files**:
    *   `src/rag/prompts/context_builder.py`: Maps metadata to reference formatting structures.
*   **Technical Design**:
    *   Inject tags like `[Doc ID: C-12, Source: FAQ.json]` next to referenced text blocks.
    *   Strict system guidelines instructing LLM to explicitly use context indices inside generated responses.
*   **Tasks**:
    *   Write string builder layouts formatting reference indices with associated metadata keys.
    *   Configure system prompts instructing agents to validate statements using citation tags.
*   **Verification Plan**:
    *   Verify prompt output matches the structural template structure.
*   **Deliverable**: Dynamic prompt compiler mapping source files to system instructions.

---

### 📌 Phase 10: Low-Latency LLM Streaming (GPT-4o-mini / Groq)
*   **Objective**: Setup asynchronous token-level LLM client connections with primary and backup LLM providers.
*   **Target Files**:
    *   `src/rag/llm/llm_client.py`: API request wrappers.
*   **Technical Design**:
    *   Primary: Groq Llama-3.1; Fallback: OpenAI GPT-4o-mini.
    *   Wrap generators in a circuit-breaker checker class to handle failures.
*   **Tasks**:
    *   Establish async streaming generators mapping response chunks.
    *   Build error catch triggers redirecting pipelines on network outages or model timeouts.
*   **Verification Plan**:
    *   Simulate Groq API outages and verify fallback transitions seamlessly.
*   **Deliverable**: An async LLM streaming module with fallback recovery logic.

---

### 📌 Phase 11: Sentence Splitter & TTS Prefetching Engine
*   **Objective**: Feed text outputs to TTS providers sentence-by-sentence in the background to prevent audio stuttering.
*   **Target Files**:
    *   [src/voice/orchestrator.py](file:///d:/AI-Hospital-Agent/src/voice/orchestrator.py): Integrated streaming voice pipeline.
    *   [src/voice/tts.py](file:///d:/AI-Hospital-Agent/src/voice/tts.py): Asynchronous audio synthesis wrapper.
*   **Technical Design**:
    *   Intercept token streaming and split sentences at punctuation boundaries.
    *   Maintain an async prefetch audio queue (`asyncio.Queue`).
*   **Tasks**:
    *   Configure split string monitors parsing final tokens during chat output generation.
    *   Initialize async playback queue pre-fetching voice segments dynamically.
*   **Verification Plan**:
    *   Verify audio playback begins in <500ms and sentences stream without overlapping pauses.
*   **Deliverable**: Sentence prefetcher module generating back-to-back audio streams.

---

### 📌 Phase 12: LangGraph Orchestrator & Tool Routing
*   **Objective**: Define conversation states, route logic, and load session memories.
*   **Target Files**:
    *   `src/rag/routing/agent_router.py`: Handles intent categorization logic.
    *   `src/rag/routing/orchestrator_graph.py`: LangGraph workflow definition.
*   **Technical Design**:
    *   Define State schema tracking conversations.
    *   Save multi-turn sessions in Redis with dynamic TTL policies.
*   **Tasks**:
    *   Define LangGraph routing workflows mapping nodes to targeted specialized agents.
    *   Wire Redis connections fetching/saving state histories mapped to session IDs.
*   **Verification Plan**:
    *   Run dummy state parameters through the Graph and trace path decisions.
*   **Deliverable**: A LangGraph orchestrator mapping conversations to target tools.

---

### 📌 Phase 13: Safety Guardrails Integration
*   **Objective**: Block diagnostic requests, prevent prescription distribution, and sanitize client inputs.
*   **Target Files**:
    *   `src/rag/guadrails/guard_manager.py`: Policy enforcement module.
*   **Technical Design**:
    *   Run input sanitization (PII check, regex blocklists).
    *   Add emergency detection routing critical health inquiries to phone numbers.
*   **Tasks**:
    *   Construct regex scrubbers cleaning phone numbers, billing keys, or emails from logging data.
    *   Configure critical trigger rules handling emergency calls instantly.
*   **Verification Plan**:
    *   Assert that emergency triggers return the rescue message instantly.
*   **Deliverable**: Guardrail inspector validating queries before processing.

---

### 📌 Phase 14: Automated Evaluation & Metrics (Evals)
*   **Objective**: Set up tests measuring context recall, factual faithfulness, and answer relevance.
*   **Target Files**:
    *   `src/rag/evaluation/eval_runner.py`: Executes automated assertions.
*   **Technical Design**:
    *   Use DeepEval or standard test suits to assert performance.
    *   Compute Faithfulness scoring based on claims verification.
*   **Tasks**:
    *   Define automated scoring scripts grading context relevance indicators.
    *   Build test suites evaluating mock QA files.
*   **Verification Plan**:
    *   Run test suite locally to verify accuracy indices.
*   **Deliverable**: Assessment pipeline producing quality reports.

---

### 📌 Phase 15: Production Deployment & Monitoring
*   **Objective**: Deploy the system securely, configure Docker containers, and set up telemetry.
*   **Target Files**:
    *   [docker-compose.yml](file:///d:/AI-Hospital-Agent/docker-compose.yml): Production configuration.
    *   `prometheus.yml`: Telemetry settings.
*   **Technical Design**:
    *   Configure reverse proxy (Nginx or Traefik) to manage SSL and route WebSockets.
    *   Expose metrics like query latency, token usage, and STT failure rates to Prometheus/Grafana.
*   **Tasks**:
    *   Construct docker-compose configuration defining all network boundaries.
    *   Define Prometheus exporters monitoring LLM response lag indices.
*   **Verification Plan**:
    *   Deploy containers locally and check health probe endpoints.
*   **Deliverable**: Production-ready container configuration with active health probes.

---

## 🛠️ Verification Checklist

Use this checklist during staging/deployment:
*   [ ] Loaders successfully parse raw files and return standard `Document` schemas.
*   [ ] Qdrant indexing runs and holds correctly embedded chunks.
*   [ ] Sparse BM25 retrieval finds keyword terms correctly.
*   [ ] RRF scoring combines dense and sparse ranks.
*   [ ] Rerank filters out low-scoring chunks.
*   [ ] Context builder formats reference lists with metadata.
*   [ ] Audio playback streams without gaps or stuttering.
*   [ ] Emergency queries redirect instantly.
*   [ ] End-to-End latency remains within the target sub-500ms SLA.
