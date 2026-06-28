# SwiggyRAG — Architecture

## System Architecture Overview

SwiggyRAG follows a **two-tier client-server architecture** with no intermediary layers. The frontend is a static single-page application that communicates with a Python REST API over HTTP. All intelligence resides in the backend, which orchestrates document ingestion, vector search, and LLM generation.

```mermaid
graph TB
    subgraph "Browser (Client)"
        FE["Frontend<br/>HTML + CSS + JS"]
    end

    subgraph "Backend Server (localhost:8000)"
        API["FastAPI App<br/>app.py"]
        ING["Ingestion Module<br/>ingest.py"]
        RAG["RAG Pipeline<br/>rag_pipeline.py"]
    end

    subgraph "Persistence (Filesystem)"
        PDF["swiggy_annual_report.pdf<br/>backend/data/"]
        IDX["faiss_index.index<br/>backend/"]
        META["metadata.pkl<br/>backend/"]
    end

    subgraph "External Services"
        GROQ["Groq API<br/>LLaMA 3.1 8B Instant"]
        HF["HuggingFace Hub<br/>(first-run model download)"]
    end

    FE -->|"POST /ask"| API
    FE -->|"POST /rebuild-index"| API
    API --> RAG
    API -->|"lazy import"| ING
    ING --> PDF
    RAG -->|"encode/search"| IDX
    RAG -->|"load/save"| META
    RAG -->|"chat.completions.create()"| GROQ
    RAG -->|"first-run download"| HF
    ING -->|"build_index()"| RAG

    style FE fill:#fff2e8,stroke:#fc8019,color:#111
    style API fill:#e0f2fe,stroke:#0284c7,color:#111
    style RAG fill:#f0fdf4,stroke:#16a34a,color:#111
    style ING fill:#fef3c7,stroke:#d97706,color:#111
    style GROQ fill:#fce7f3,stroke:#db2777,color:#111
```

---

## Frontend Architecture

### Technology

Vanilla HTML5 + CSS + JavaScript (ES6+). No framework, no build step, no bundler.

### Page Structure

The entire UI is a **single HTML page** (`index.html`) with three logical sections:

```mermaid
graph TD
    subgraph "index.html"
        H["Header<br/>(Logo, Title, Badge)"]
        M["Main<br/>(Search Container)"]
        R["Results Container<br/>(Answer Card + Context Card)"]
        F["Footer<br/>(Tech Stack + Rebuild Button)"]
        T["Toast Overlay"]
    end

    H --> M
    M --> R
    R --> F
    T -.->|"fixed position"| M

    style H fill:#f9fafb,stroke:#e5e7eb
    style M fill:#fff2e8,stroke:#fc8019
    style R fill:#f0fdf4,stroke:#16a34a
    style F fill:#f9fafb,stroke:#e5e7eb
    style T fill:#1f2937,stroke:#374151,color:#fff
```

### UI Components (Implemented as DOM Sections)

| Component | DOM ID/Class | Purpose |
|---|---|---|
| Search Input | `#question-input` | Text input for user questions |
| Submit Button | `#submit-btn` | Triggers question submission |
| Quick Prompts | `.prompt-btn` (×5) | Pre-built suggested questions |
| Loading Indicator | `#loading` | Three-dot bounce animation + status text |
| Answer Card | `.answer-card` | Displays LLM-generated answer |
| Sources Summary | `#sources-summary` | Page numbers with color-coded relevance bars |
| Context Toggle | `#toggle-context` | Expand/collapse button for raw context |
| Context Content | `#context-content` | Raw text chunks from FAISS retrieval |
| Rebuild Button | `#rebuild-btn` | Triggers `/rebuild-index` |
| Toast | `#toast` | Transient notification messages |

### State Management

There is no application state beyond DOM visibility toggling. The frontend is **stateless** — each question submission is a fresh HTTP request. State is managed entirely through CSS class toggling:

- `.hidden` class (maps to `display: none !important`) controls visibility of loading, results, context, sources, and toast elements
- `.active` class on `#toggle-context` rotates the chevron icon

### Design System

The CSS uses a centralized custom property system in `:root`:

| Token | Value | Usage |
|---|---|---|
| `--primary-color` | `#fc8019` | Swiggy orange — buttons, accents, borders |
| `--primary-dark` | `#d6640c` | Hover states, header text |
| `--primary-light` | `#fff2e8` | Light orange backgrounds, focus rings |
| `--bg-gradient` | `linear-gradient(135deg, #f9fafb, #f3f4f6)` | Page background |
| `--surface-color` | `#ffffff` | Card backgrounds |
| `--border-color` | `#e5e7eb` | Dividers, input borders |
| `--success-color` | `#10b981` | High-relevance score bars |
| `--shadow-md` | `0 4px 6px ...` | Card elevation |

---

## Backend Architecture

### Framework & Runtime

- **FastAPI** on **Uvicorn** (ASGI)
- Single-process, single-threaded (default uvicorn config)
- `--reload` flag enables hot-reloading during development

### Module Dependency Graph

```mermaid
graph LR
    APP["app.py<br/>(API Gateway)"]
    RAG["rag_pipeline.py<br/>(RAG Core)"]
    ING["ingest.py<br/>(Document Processor)"]
    ENV[".env<br/>(Secrets)"]

    APP -->|"imports retrieve, generate_answer"| RAG
    APP -->|"lazy imports process_pdf<br/>(only on /rebuild-index)"| ING
    APP -->|"lazy imports build_index<br/>(only on /rebuild-index)"| RAG
    APP -->|"load_dotenv()"| ENV
    RAG -->|"Groq(api_key=os.getenv())"| ENV

    style APP fill:#e0f2fe,stroke:#0284c7
    style RAG fill:#f0fdf4,stroke:#16a34a
    style ING fill:#fef3c7,stroke:#d97706
    style ENV fill:#fce7f3,stroke:#db2777
```

### Import Strategy

| Module | Import Timing | Rationale |
|---|---|---|
| `rag_pipeline.retrieve` | **Eager** (top of `app.py`) | Needed on every `/ask` request; also triggers `SentenceTransformer` model loading at startup |
| `rag_pipeline.generate_answer` | **Eager** (top of `app.py`) | Same module as `retrieve` |
| `ingest.process_pdf` | **Lazy** (inside `rebuild_index()`) | Only needed during index rebuild; avoids loading pypdf/langchain on every request |
| `rag_pipeline.build_index` | **Lazy** (inside `rebuild_index()`) | Already loaded eagerly via the module, but re-imported locally for clarity |

---

## Request Lifecycle

### `/ask` — Question Answering

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend (script.js)
    participant API as FastAPI (app.py)
    participant RAG as rag_pipeline.py
    participant FAISS as FAISS Index (disk)
    participant Groq as Groq API

    User->>FE: Types question + clicks "Analyze"
    FE->>FE: Validate non-empty input
    FE->>FE: Show loading animation
    FE->>FE: Disable submit button
    FE->>API: POST /ask { question: "..." }

    API->>API: Resolve index_path & meta_path (relative to __file__)
    API->>RAG: retrieve(question, top_k=5, index_path, meta_path)
    RAG->>FAISS: faiss.read_index(index_path)
    RAG->>RAG: pickle.load(metadata.pkl)
    RAG->>RAG: embedder.encode([query])
    RAG->>FAISS: index.search(query_embedding, 5)
    FAISS-->>RAG: distances[], indices[]
    RAG-->>API: [{chunk_id, page, content, score}, ...]

    alt Top-1 score > 1.5 (low confidence)
        API-->>FE: { answer: "Insufficient information...", sources: [] }
    else Top-1 score ≤ 1.5 (sufficient confidence)
        API->>RAG: generate_answer(question, chunks)
        RAG->>RAG: Format prompt with context
        RAG->>Groq: chat.completions.create(model, messages, temp=0, max_tokens=500)
        Groq-->>RAG: Generated answer text
        RAG-->>API: answer string
        API-->>FE: { answer: "...", sources: [{page, content, score}] }
    end

    FE->>FE: Hide loading, show results
    FE->>FE: Render answer text
    FE->>FE: Render source bars (L2 → percentage)
    FE->>FE: Populate context chunks
    FE->>FE: Re-enable submit button
```

### `/rebuild-index` — Knowledge Base Refresh

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend (script.js)
    participant API as FastAPI (app.py)
    participant ING as ingest.py
    participant RAG as rag_pipeline.py
    participant FS as Filesystem

    User->>FE: Clicks "Refresh Knowledge Base"
    FE->>FE: Show toast "Rebuilding Vector Index..."
    FE->>API: POST /rebuild-index

    API->>API: Lazy import ingest.process_pdf
    API->>API: Lazy import rag_pipeline.build_index
    API->>API: Resolve pdf_path, index_path, meta_path

    API->>ING: process_pdf(pdf_path)
    ING->>FS: PdfReader(pdf_path)
    ING->>ING: Extract text per page
    ING->>ING: clean_text() — collapse whitespace
    ING->>ING: RecursiveCharacterTextSplitter(800, 150)
    ING-->>API: [{chunk_id, page, content}, ...]

    alt chunks is empty
        API-->>FE: 404 "PDF file not found"
    else chunks exist
        API->>RAG: build_index(chunks, index_path, meta_path)
        RAG->>RAG: embedder.encode(all chunk texts)
        RAG->>RAG: faiss.IndexFlatL2(384)
        RAG->>RAG: index.add(embeddings)
        RAG->>FS: faiss.write_index(index_path)
        RAG->>FS: pickle.dump(metadata, meta_path)
        RAG-->>API: index, metadata
        API-->>FE: { status: "success", message: "Built index with N chunks" }
    end

    FE->>FE: Show success/error toast
```

---

## Authentication & Authorization

**There is none.** The API has no authentication middleware, no API keys for client access, no JWT tokens, no session management. Any client that can reach port 8000 can call any endpoint.

The only external authentication is the `GROQ_API_KEY` used server-side to authenticate with the Groq inference platform.

### CORS Configuration

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Any origin
    allow_credentials=True,
    allow_methods=["*"],       # Any HTTP method
    allow_headers=["*"],       # Any header
)
```

This is maximally permissive. Acceptable for local development but inappropriate for production.

---

## Data Flow

### Data at Rest

```mermaid
graph LR
    PDF["swiggy_annual_report.pdf<br/>~13 MB raw PDF"]
    -->|"process_pdf()"| CHUNKS["In-memory chunks<br/>[{chunk_id, page, content}]"]
    -->|"build_index()"| EMB["Embeddings<br/>float32 array [N × 384]"]

    EMB -->|"faiss.write_index()"| IDX["faiss_index.index<br/>~134 KB binary"]
    CHUNKS -->|"pickle.dump()"| META["metadata.pkl<br/>~60 KB pickle"]

    style PDF fill:#fef3c7,stroke:#d97706
    style CHUNKS fill:#e0f2fe,stroke:#0284c7
    style EMB fill:#f0fdf4,stroke:#16a34a
    style IDX fill:#fce7f3,stroke:#db2777
    style META fill:#fce7f3,stroke:#db2777
```

### Data Transformation Pipeline

| Stage | Input | Transformation | Output |
|---|---|---|---|
| 1. PDF Extraction | `swiggy_annual_report.pdf` | `pypdf.PdfReader.extract_text()` | Raw text per page |
| 2. Cleaning | Raw text | `re.sub(r'\s+', ' ', text).strip()` | Normalized whitespace text |
| 3. Chunking | Cleaned text | `RecursiveCharacterTextSplitter(800, 150)` | List of text chunks (≤800 chars) |
| 4. Metadata Tagging | Chunks | Add `chunk_id` (sequential), `page` (1-indexed) | `[{chunk_id, page, content}]` |
| 5. Embedding | Chunk text | `SentenceTransformer.encode()` | `float32` vectors `[N × 384]` |
| 6. Indexing | Embeddings | `faiss.IndexFlatL2(384).add()` | FAISS index (brute-force L2) |
| 7. Serialization | Index + metadata | `faiss.write_index()` + `pickle.dump()` | Two files on disk |

### Query Data Flow

| Stage | Input | Transformation | Output |
|---|---|---|---|
| 1. Query Embedding | User question string | `SentenceTransformer.encode([query])` | `float32` vector `[1 × 384]` |
| 2. FAISS Search | Query vector + index | `index.search(vector, k=5)` | `distances[5]`, `indices[5]` |
| 3. Metadata Lookup | FAISS indices | `metadata[idx]` for each result | Chunk dicts with `page`, `content` |
| 4. Score Attachment | L2 distances | Cast to Python float, add as `score` field | Chunks with scores |
| 5. Threshold Check | Top-1 score | Compare against `SIMILARITY_THRESHOLD` (1.5) | Pass/reject decision |
| 6. Prompt Construction | Question + chunks | String format template with page-labeled context | Formatted prompt string |
| 7. LLM Generation | Formatted prompt | Groq API call (`temperature=0`, `max_tokens=500`) | Answer text |

---

## Database Architecture

**There is no traditional database.** All persistent state is stored as two flat files:

### `faiss_index.index`

| Property | Value |
|---|---|
| Format | FAISS binary serialization |
| Index Type | `IndexFlatL2` (brute-force exact L2 search) |
| Dimension | 384 (matches `all-MiniLM-L6-v2` output) |
| Size | ~134 KB (for the demo PDF's ~few chunks) |
| Location | `backend/faiss_index.index` |
| Created by | `rag_pipeline.build_index()` |
| Read by | `rag_pipeline.load_index()` → `retrieve()` |

### `metadata.pkl`

| Property | Value |
|---|---|
| Format | Python pickle (protocol default) |
| Structure | `dict[int, dict]` — maps FAISS vector index → chunk metadata |
| Chunk schema | `{ chunk_id: int, page: int, content: str }` |
| Size | ~60 KB |
| Location | `backend/metadata.pkl` |
| Security risk | `pickle.load()` can execute arbitrary code if file is tampered |

### Entity Relationships

```mermaid
erDiagram
    PDF_DOCUMENT {
        string filename
        int page_count
    }
    PAGE {
        int page_number
        string raw_text
    }
    CHUNK {
        int chunk_id PK
        int page FK
        string content
    }
    EMBEDDING {
        int vector_index PK
        float384 vector
    }

    PDF_DOCUMENT ||--o{ PAGE : "contains"
    PAGE ||--o{ CHUNK : "split into"
    CHUNK ||--|| EMBEDDING : "encoded as"
```

---

## Dependency Graph (Backend Python)

```mermaid
graph TD
    subgraph "Application Layer"
        APP["app.py"]
    end

    subgraph "Domain Layer"
        RAG["rag_pipeline.py"]
        ING["ingest.py"]
    end

    subgraph "Third-Party Libraries"
        FAST["fastapi"]
        PYDN["pydantic"]
        CORS["fastapi.middleware.cors"]
        DOTENV["python-dotenv"]
        PYPDF["pypdf"]
        LC["langchain<br/>(RecursiveCharacterTextSplitter)"]
        ST["sentence-transformers"]
        FA["faiss-cpu"]
        GQ["groq"]
        NP["numpy"]
        PK["pickle (stdlib)"]
        RE["re (stdlib)"]
        OS["os (stdlib)"]
    end

    APP --> FAST
    APP --> PYDN
    APP --> CORS
    APP --> DOTENV
    APP --> RAG
    APP --> ING

    RAG --> FA
    RAG --> ST
    RAG --> NP
    RAG --> PK
    RAG --> GQ
    RAG --> OS

    ING --> PYPDF
    ING --> LC
    ING --> RE
    ING --> OS

    style APP fill:#e0f2fe,stroke:#0284c7
    style RAG fill:#f0fdf4,stroke:#16a34a
    style ING fill:#fef3c7,stroke:#d97706
```

### Dependency Purpose Table

| Package | Used By | Purpose | Critical? |
|---|---|---|---|
| `fastapi` | `app.py` | HTTP framework, routing, request validation | ✅ Yes |
| `uvicorn` | CLI / `__main__` | ASGI server | ✅ Yes |
| `pydantic` | `app.py` | Request/response model validation | ✅ Yes (via FastAPI) |
| `python-dotenv` | `app.py` | Load `.env` file into `os.environ` | ✅ Yes |
| `pypdf` | `ingest.py` | Extract text from PDF pages | ✅ Yes |
| `langchain` | `ingest.py` | `RecursiveCharacterTextSplitter` for chunking | ✅ Yes |
| `langchain-community` | (transitive) | Required by langchain | ⚠️ Indirect |
| `sentence-transformers` | `rag_pipeline.py` | Generate 384-dim text embeddings | ✅ Yes |
| `faiss-cpu` | `rag_pipeline.py` | Vector similarity search | ✅ Yes |
| `groq` | `rag_pipeline.py` | LLM API client for answer generation | ✅ Yes |
| `numpy` | `rag_pipeline.py` | Array manipulation for embeddings | ✅ Yes (via sentence-transformers) |
| `tqdm` | (transitive) | Progress bars for embedding generation | ⚠️ Indirect |
| `openai` | **UNUSED** | Listed in requirements but never imported | ❌ Dead |
| `python-multipart` | **UNUSED** | Listed in requirements but no file upload endpoints | ❌ Dead |

---

## Deployment Architecture

### Current (Local Development Only)

```mermaid
graph TB
    subgraph "Developer Machine"
        subgraph "Terminal 1"
            UV["uvicorn app:app<br/>:8000"]
        end
        subgraph "Terminal 2"
            HS["python -m http.server<br/>:8080"]
        end
        subgraph "Browser"
            BR["http://localhost:8080"]
        end
    end

    subgraph "Cloud"
        GQ["Groq API<br/>api.groq.com"]
    end

    BR -->|"fetch()"| UV
    UV -->|"HTTPS"| GQ
    HS -->|"serves static files"| BR
```

### Scalability Considerations

| Concern | Current State | Impact | Mitigation Path |
|---|---|---|---|
| **FAISS index type** | `IndexFlatL2` (brute-force) | O(n) search; fine for < 10K vectors | Switch to `IndexIVFFlat` or `IndexHNSW` |
| **Index reload per request** | `load_index()` called on every `/ask` | Disk I/O on every query | Cache in memory (module-level or singleton) |
| **Synchronous embedding** | Blocking call in ASGI event loop | One request at a time | Use `run_in_executor` or async embedding |
| **Synchronous rebuild** | Blocks entire server during index build | Server unresponsive during rebuild | Background task (FastAPI `BackgroundTasks` or Celery) |
| **Single-process server** | Default uvicorn with `--reload` | No parallelism | Multi-worker deployment (`-w 4`) |
| **No caching** | LLM called on every identical question | Wasted API calls and latency | Redis or in-memory LRU cache |
| **File-based persistence** | `.index` and `.pkl` on local disk | No redundancy, no concurrent access | PostgreSQL + pgvector or Pinecone |

---

## Design Patterns

| Pattern | Where | Implementation |
|---|---|---|
| **RAG (Retrieval-Augmented Generation)** | Entire backend | Core architectural pattern: retrieve → augment prompt → generate |
| **Gateway / Controller** | `app.py` | Thin API layer that delegates to domain modules |
| **Pipeline** | `ingest.py` → `rag_pipeline.py` | Sequential data transformation: PDF → chunks → embeddings → index |
| **Repository** (informal) | `load_index()` / `build_index()` | Encapsulates persistence of FAISS index + metadata |
| **Template Method** | `generate_answer()` | Fixed prompt template filled with dynamic context |
| **Lazy Loading** | `rebuild_index()` endpoint | Defers `import ingest` until actually needed |
| **Guard Clause** | `SIMILARITY_THRESHOLD` check in `/ask` | Short-circuits response for low-confidence retrievals |
| **Observer** (DOM events) | `script.js` | Event listeners for click, keypress, DOMContentLoaded |

---

## Design Trade-offs

| Decision | Trade-off | Rationale |
|---|---|---|
| **`IndexFlatL2` over approximate search** | Slower at scale, but exact results | Dataset is tiny (< 100 vectors from a 2-page demo PDF); exactness preferred |
| **Sentence Transformers over OpenAI embeddings** | Lower quality embeddings, but free and local | No cost per query; no network call for embeddings; works offline |
| **Groq over local LLM** | Requires internet + API key, but very fast inference | Groq provides sub-second inference for LLaMA 3.1; local LLM would need GPU |
| **Pickle over JSON for metadata** | Security risk, but preserves Python types exactly | Simple dict serialization; no complex objects |
| **No database** | No concurrent access, no transactions, no backup | Simplicity for a demo project; FAISS files are the "database" |
| **Vanilla JS over React/Vue** | No component reuse, no virtual DOM, harder to scale | Minimal dependencies; no build step; fast to prototype |
| **Wildcard CORS** | Insecure, but convenient for local dev | Frontend and backend run on different ports |
| **`temperature=0`** | Deterministic but less creative answers | Financial data requires precision, not creativity |
| **800-char chunks with 150-char overlap** | Smaller chunks may lose context; overlap adds redundancy | Balances retrieval precision with context completeness |

---

## Extension Points

> Where to add new functionality with minimal disruption.

| Extension | Entry Point | Impact |
|---|---|---|
| **New LLM provider** | `rag_pipeline.py` → `generate_answer()` | Add provider selection logic based on `LLM_PROVIDER` env var |
| **Multi-document support** | `ingest.py` → `process_pdf()` | Accept a directory of PDFs; tag chunks with document name |
| **Streaming responses** | `app.py` → new `/ask-stream` endpoint | Use FastAPI `StreamingResponse` + Groq streaming |
| **Chat history** | `app.py` → modify `/ask` to accept `conversation_id` | Add message history to prompt context |
| **File upload** | `app.py` → new `/upload` endpoint | Accept PDF via multipart form; `python-multipart` already in deps |
| **Persistent caching** | `rag_pipeline.py` → wrap `generate_answer()` | Hash (question + context) → cache answer |
| **User authentication** | `app.py` → FastAPI dependency injection | Add OAuth2/JWT middleware |
| **Dark mode** | `frontend/style.css` → `:root` overrides | Add `[data-theme="dark"]` CSS custom property overrides |
| **WebSocket real-time** | `app.py` → FastAPI WebSocket endpoint | Stream LLM tokens to frontend in real-time |
