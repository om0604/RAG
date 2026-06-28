# SwiggyRAG — Project Context

## Executive Summary

SwiggyRAG is a **Retrieval-Augmented Generation (RAG) question-answering application** that allows users to ask natural-language questions about the **Swiggy FY23 Annual Report** and receive source-grounded, LLM-generated answers. The system ingests a PDF document, chunks it, creates vector embeddings, stores them in a FAISS index, retrieves semantically similar chunks at query time, and feeds them as context to an LLM (Groq-hosted LLaMA 3.1 8B) that synthesizes a final answer. A hallucination-prevention guard rejects low-confidence retrievals.

The project is a **monorepo** with two independently runnable components:

| Layer | Technology | Runtime |
|---|---|---|
| **Backend API** | Python 3 · FastAPI · FAISS · Sentence Transformers · Groq SDK | `uvicorn` on port 8000 |
| **Frontend UI** | Vanilla HTML / CSS / JavaScript | Any static file server (e.g. `python -m http.server 8080`) |

There is **no database**, **no Docker**, **no CI/CD**, **no authentication**, and **no test suite**. The entire state is persisted as two flat files (`faiss_index.index` and `metadata.pkl`) next to the backend source.

---

## Project Purpose & Business Domain

| Dimension | Detail |
|---|---|
| **Domain** | Financial document intelligence / corporate disclosure analysis |
| **Business Entity** | Swiggy (Indian food delivery and quick-commerce platform) |
| **Document** | Swiggy Annual Report FY2023 (PDF) |
| **End User** | Financial analysts, investors, journalists, or anyone seeking structured answers from an annual report |
| **Value Proposition** | Eliminates manual PDF scanning by enabling conversational Q&A with automatic citation of page numbers and relevance scores |
| **Hallucination Stance** | Strict — if the best retrieval chunk has an L2 distance > 1.5 from the query embedding, the system refuses to answer rather than risk fabrication |

---

## Features

1. **PDF Ingestion** — Parse a multi-page PDF, clean whitespace, and split into overlapping 800-character chunks.
2. **Vector Index Build** — Embed each chunk with `all-MiniLM-L6-v2`, store in a FAISS `IndexFlatL2` index, serialize to disk.
3. **Semantic Retrieval** — Given a user query, embed it, search FAISS for top-K nearest chunks, return with L2 distance scores.
4. **LLM Answer Generation** — Construct a grounded prompt with retrieved context and call Groq's LLaMA 3.1 8B (`temperature=0`, `max_tokens=500`).
5. **Hallucination Guard** — If top-1 chunk L2 distance > 1.5, return a safe "insufficient information" response with no sources.
6. **Source Citation** — Every answer displays the source page numbers with color-coded relevance bars.
7. **Expandable Context Viewer** — Users can inspect the raw text chunks that informed the answer.
8. **Index Rebuild** — A single button / API call re-ingests the PDF and rebuilds the vector index on the fly.
9. **Suggested Questions** — Five pre-built prompt buttons for quick exploration.
10. **Toast Notifications** — Transient status messages for rebuild success/failure and errors.

---

## Tech Stack

### Backend

| Component | Technology | Purpose |
|---|---|---|
| Web Framework | **FastAPI** | REST API with Pydantic validation |
| ASGI Server | **Uvicorn** | Serves FastAPI app |
| PDF Parsing | **pypdf** (`PdfReader`) | Extracts text from each PDF page |
| Text Splitting | **LangChain** (`RecursiveCharacterTextSplitter`) | Splits cleaned text into overlapping chunks |
| Embeddings | **Sentence Transformers** (`all-MiniLM-L6-v2`) | Produces 384-dim dense vectors for text |
| Vector Store | **FAISS** (`faiss-cpu`, `IndexFlatL2`) | Brute-force L2 nearest-neighbor search |
| LLM Client | **Groq Python SDK** | Calls Groq-hosted LLaMA 3.1 8B Instant |
| Environment | **python-dotenv** | Loads `.env` for API keys |
| Serialization | **pickle** (stdlib) | Persists chunk metadata alongside FAISS index |

### Frontend

| Component | Technology |
|---|---|
| Markup | HTML5 |
| Styling | Vanilla CSS with CSS custom properties (Swiggy-orange design system) |
| Logic | Vanilla JavaScript (ES6+, `fetch` API) |
| Fonts | Google Fonts — Inter |
| Icons | Font Awesome 6 |

### Utilities

| File | Technology | Purpose |
|---|---|---|
| `generate_pdf.py` | **fpdf** | Creates a minimal 2-page synthetic Swiggy Annual Report PDF for testing/demo |

---

## Folder Structure

```
SwiggyRAG/
├── .gitignore                  # Ignores .env, venv, __pycache__, IDE files
├── README.md                   # Setup instructions, sample questions, limitations
├── generate_pdf.py             # Utility: creates a synthetic demo PDF
│
├── backend/
│   ├── .env                    # GROQ_API_KEY (gitignored in practice — currently tracked!)
│   ├── .env.example            # Template: LLM_PROVIDER + GROQ_API_KEY placeholder
│   ├── requirements.txt        # pip dependencies (12 packages, unpinned)
│   ├── app.py                  # FastAPI application — 2 endpoints (/ask, /rebuild-index)
│   ├── ingest.py               # PDF parsing and chunking logic
│   ├── rag_pipeline.py         # Embedding, FAISS indexing, retrieval, LLM generation
│   ├── faiss_index.index       # Serialized FAISS vector index (binary, ~134 KB)
│   ├── metadata.pkl            # Pickled dict mapping FAISS IDs → chunk metadata
│   ├── data/
│   │   └── swiggy_annual_report.pdf   # Source document (~13 MB)
│   └── __pycache__/            # Python bytecode cache (gitignored)
│
└── frontend/
    ├── index.html              # Single-page HTML (search bar, results, footer)
    ├── style.css               # Full design system (504 lines, CSS custom properties)
    └── script.js               # Client-side logic (fetch /ask, render results, rebuild index)
```

---

## Major Modules

### 1. `backend/app.py` — API Gateway

The FastAPI application. Defines two POST endpoints and the CORS configuration. This is the **only entry point** to the backend. It imports from `rag_pipeline` (eagerly) and `ingest` (lazily, only on rebuild).

### 2. `backend/ingest.py` — Document Ingestion

Reads a PDF file, extracts text page-by-page, cleans whitespace, and splits into overlapping chunks. Returns a list of `{chunk_id, page, content}` dicts. This module has **no LLM or embedding dependency** — it is pure document processing.

### 3. `backend/rag_pipeline.py` — RAG Core

The heart of the system. Contains four functions:
- `build_index()` — Embed chunks → create FAISS index → serialize to disk
- `load_index()` — Deserialize FAISS index + metadata from disk
- `retrieve()` — Embed a query → FAISS search → return top-K chunks with L2 scores
- `generate_answer()` — Format a grounded prompt → call Groq API → return LLM text

**Side effect at import time**: instantiates `SentenceTransformer('all-MiniLM-L6-v2')` as a module-level global, which downloads the model on first run (~90 MB) and consumes RAM thereafter.

### 4. `frontend/script.js` — Client Controller

All client-side logic. Handles form submission, calls `/ask` and `/rebuild-index`, renders answer text, builds source bars, manages loading/toast UI state. Converts L2 distances to 0–100% relevance percentages for display.

### 5. `frontend/style.css` — Design System

504-line CSS file with a Swiggy-branded design system using CSS custom properties. Defines the visual language: orange accent (`#fc8019`), Inter font, card shadows, pill badges, animated loading dots, toast notifications, and responsive layout.

### 6. `frontend/index.html` — Page Shell

Single-page HTML document. Contains the search bar, five suggested-question buttons, a loading indicator, an answer card with source bars, an expandable context viewer, and a footer with a "Refresh Knowledge Base" button.

### 7. `generate_pdf.py` — Test Data Generator

A standalone script using `fpdf` to create a minimal 2-page synthetic Swiggy Annual Report PDF. Useful for bootstrapping the demo without needing the real 13 MB document.

---

## Application Flow

### Query Flow (Happy Path)

```
User types question → clicks "Analyze" or presses Enter
  ↓
script.js: POST /ask { question: "..." }
  ↓
app.py: ask_question() — loads FAISS index + metadata from disk
  ↓
rag_pipeline.py: retrieve() — encodes query → FAISS L2 search → returns top-5 chunks with scores
  ↓
app.py: checks if top-1 score > 1.5 (SIMILARITY_THRESHOLD)
  ├── YES → returns { answer: "Insufficient information...", sources: [] }
  └── NO  → calls rag_pipeline.generate_answer()
              ↓
            rag_pipeline.py: formats prompt with context → POST to Groq API (LLaMA 3.1 8B)
              ↓
            Returns generated text
  ↓
app.py: returns { answer: "...", sources: [{page, content, score}, ...] }
  ↓
script.js: renders answer text, source bars (color-coded), context chunks
```

### Index Rebuild Flow

```
User clicks "Refresh Knowledge Base"
  ↓
script.js: POST /rebuild-index
  ↓
app.py: rebuild_index() — lazy imports ingest.process_pdf + rag_pipeline.build_index
  ↓
ingest.py: reads PDF → extracts text → cleans → splits into 800-char chunks (150 overlap)
  ↓
rag_pipeline.py: build_index() — encodes all chunks → builds IndexFlatL2 → writes .index + .pkl
  ↓
Returns { status: "success", message: "Successfully built index with N chunks." }
  ↓
script.js: shows success toast
```

---

## Environment Variables

| Variable | File | Required | Default | Purpose |
|---|---|---|---|---|
| `LLM_PROVIDER` | `backend/.env` | No | (unused in code) | Informational; the code hardcodes Groq usage |
| `GROQ_API_KEY` | `backend/.env` | **Yes** | None | Authentication key for Groq API |
| `GROQ_MODEL` | `backend/.env` | No | `llama-3.1-8b-instant` | Model identifier passed to Groq SDK |

> **Note**: `LLM_PROVIDER` is defined in `.env.example` but never read by any Python code. It appears to be a documentation-only convention. The backend always uses Groq regardless of this value.

---

## Build & Deployment

### Prerequisites

- Python 3.9+ (for `list[Source]` type hint syntax in Pydantic models)
- A valid Groq API key

### Backend Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
# Copy .env.example → .env and set GROQ_API_KEY
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Setup

```bash
cd frontend
python -m http.server 8080     # or any static file server
```

### First Run

1. Place the actual Swiggy Annual Report PDF at `backend/data/swiggy_annual_report.pdf`
2. Open `http://localhost:8080`
3. Click **"Refresh Knowledge Base"** to trigger PDF ingestion and FAISS index build

### No CI/CD / No Docker

There is no `Dockerfile`, `docker-compose.yml`, GitHub Actions workflow, or any deployment automation. The project is designed for local development only.

---

## Coding Conventions

| Convention | Detail |
|---|---|
| **Python style** | PEP 8, minimal docstrings, no type annotations beyond Pydantic models |
| **Import style** | Standard library → third-party → local; lazy imports used in `/rebuild-index` endpoint |
| **Frontend style** | Vanilla JS with no bundler/transpiler; all DOM refs cached at `DOMContentLoaded` |
| **CSS methodology** | Component-scoped via class names; CSS custom properties for design tokens |
| **Error handling** | Python: try/except → HTTPException(500); JS: try/catch → toast notification |
| **State persistence** | Two flat files on disk (`.index` + `.pkl`); no database |
| **No tests** | Zero unit, integration, or end-to-end tests exist |
| **No linting config** | No `.flake8`, `pyproject.toml`, `.eslintrc`, or `prettier` config |

---

## Known Issues & Technical Debt

| # | Issue | Severity | Detail |
|---|---|---|---|
| 1 | **Committed `.env` file** | 🟡 Medium | The `.env` file was committed to git before the ignore rule was effective. The real `GROQ_API_KEY` has been removed, but the file is still tracked. |
| 2 | **Unpinned dependencies** | 🟡 Medium | `requirements.txt` has no version pins. A future `pip install` could pull breaking changes. |
| 3 | **Pickle deserialization risk** | 🟡 Medium | `metadata.pkl` is loaded with `pickle.load()` which can execute arbitrary code if the file is tampered with. |
| 4 | **Wildcard CORS** | 🟡 Medium | `allow_origins=["*"]` allows any domain to call the API. Acceptable for local dev, problematic in production. |
| 5 | **`openai` package unused** | 🟢 Low | Listed in `requirements.txt` but never imported anywhere. Dead dependency. |
| 6 | **`python-multipart` unused** | 🟢 Low | Listed in `requirements.txt` but not used (no file upload endpoints). |
| 7 | **`LLM_PROVIDER` env var unused** | 🟢 Low | Defined in `.env.example` but never read by code. |
| 8 | **No input sanitization on frontend** | 🟡 Medium | `source.content` is injected into DOM via `innerHTML` without escaping. If a PDF contained HTML/JS, it could cause XSS. |
| 9 | **Module-level model loading** | 🟢 Low | `SentenceTransformer` is instantiated at import time in `rag_pipeline.py`, adding ~2-5 seconds to cold start. |
| 10 | **No pagination / rate limiting** | 🟢 Low | The API has no request throttling. |
| 11 | **Synchronous PDF processing** | 🟡 Medium | `/rebuild-index` blocks the event loop during PDF parsing + embedding. For large PDFs, this could timeout. |
| 12 | **No test suite** | 🟡 Medium | Zero tests exist. |

---

## Development Workflow

1. Ensure Python venv is active and `.env` has a valid `GROQ_API_KEY`
2. Start backend: `uvicorn app:app --host 0.0.0.0 --port 8000 --reload`
3. Start frontend: `python -m http.server 8080` from `frontend/`
4. Open `http://localhost:8080`
5. Click "Refresh Knowledge Base" if the FAISS index doesn't exist yet
6. Ask questions via the search bar or suggested prompts

### Git History (5 commits, single branch)

```
0743686 final fixes to readme and index
9c56d2d added more questions to the ui
5f3d73b final fixes to readme and index
20a822d added frontend html and css
4986cc1 working on backend rag pipeline
```

---

## Glossary

| Term | Definition |
|---|---|
| **RAG** | Retrieval-Augmented Generation — a pattern where an LLM's response is grounded in retrieved document chunks rather than relying solely on training data |
| **FAISS** | Facebook AI Similarity Search — a library for efficient nearest-neighbor search on dense vectors |
| **IndexFlatL2** | A FAISS index type that performs brute-force L2 (Euclidean) distance search. Exact but slow for millions of vectors. |
| **L2 Distance** | Euclidean distance between two vectors. Lower = more similar. 0.0 = identical. |
| **Chunk** | A segment of text extracted from the PDF, typically 800 characters with 150-character overlap |
| **Embedding** | A 384-dimensional dense vector representation of a text chunk, produced by `all-MiniLM-L6-v2` |
| **Groq** | An AI inference platform that hosts LLMs (used here for LLaMA 3.1 8B Instant) |
| **Hallucination** | When an LLM generates information not present in the source material |
| **Similarity Threshold** | The L2 distance cutoff (1.5) above which the system refuses to answer |

---

## AI Quick Start

> **If you are an AI assistant picking up this project, here is what you need to know to be productive immediately.**

### Architecture in one sentence
A Python FastAPI backend serves a `/ask` endpoint that embeds a user question, retrieves the top-5 nearest PDF chunks from a FAISS index, feeds them as context to Groq's LLaMA 3.1, and returns the answer with source citations to a vanilla JS frontend.

### Key files to modify by task

| Task | Files to Touch |
|---|---|
| Add a new API endpoint | `backend/app.py` |
| Change chunking strategy | `backend/ingest.py` (line 20-24: `chunk_size`, `chunk_overlap`) |
| Change embedding model | `backend/rag_pipeline.py` (line 8: `EMBEDDING_MODEL`) — also rebuild index |
| Change LLM model or prompt | `backend/rag_pipeline.py` (lines 66-94: `generate_answer()`) |
| Change similarity threshold | `backend/app.py` (line 34: `SIMILARITY_THRESHOLD`) |
| Change UI styling | `frontend/style.css` (CSS custom properties at `:root`) |
| Add new suggested questions | `frontend/index.html` (lines 34-46: `.quick-prompts`) |
| Change API base URL | `frontend/script.js` (line 1: `API_BASE_URL`) |

### Critical constraints
- The FAISS index and metadata pickle must be co-located with `app.py` (paths are resolved relative to `__file__`)
- The SentenceTransformer model (`all-MiniLM-L6-v2`) must match between index build and query time
- The `GROQ_API_KEY` must be set in `backend/.env`
- Frontend expects backend at `http://localhost:8000`
- No test suite exists — manual testing only
