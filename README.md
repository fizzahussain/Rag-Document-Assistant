<div align="center">

# 🧠 INDEX

### Local-first document intelligence with RAG, OCR, speech-to-text, vector search, and private LLM inference.

Upload documents, extract native or scanned content, build semantic vectors, ask grounded questions, continue multi-turn conversations, speak queries by voice, and receive traceable answers through a Dockerized FastAPI + Gradio application.

<p>
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Gradio-UI-F97316?style=for-the-badge&logo=gradio&logoColor=white" alt="Gradio" />
  <img src="https://img.shields.io/badge/Ollama-Local_AI-111111?style=for-the-badge" alt="Ollama" />
  <img src="https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL pgvector" />
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
</p>

</div>

## 🎥 Demo

[▶ Watch the RAG Document Assistant demo](https://github.com/user-attachments/assets/1405cbca-9955-4bce-a0ab-7c2c6cd94b9d)

# ✨ Why This Project Is Interesting

This project goes well beyond a basic “chat with PDF” demo.

It brings together several AI and software-engineering problems that normally live in separate projects:

<table>
<tr>
<td width="33%" valign="top">

## 📄 Understand Documents

- Native PDF extraction
- Selective **Tesseract OCR**
- DOCX, TXT, Markdown, CSV, HTML and JSON ingestion
- File validation and hashing
- Page-aware metadata
- Persistent document lifecycle

</td>
<td width="33%" valign="top">

## 🔎 Retrieve Meaning

- Context-aware chunking
- Physical chunk overlap
- Rolling context summaries
- **Ollama embeddings**
- `nomic-embed-text`
- **pgvector cosine search**
- **HNSW vector index**

</td>
<td width="33%" valign="top">

## 💬 Answer Naturally

- Local **Ollama LLM**
- `llama3.2`
- Grounded prompts
- Source citations
- Streaming responses
- Conversation memory
- Follow-up resolution
- Voice questions through **faster-whisper**

</td>
</tr>
</table>

The result is a private document workspace where retrieval, AI generation, OCR, audio, authentication, storage, and deployment concerns all meet in one system.

---

# 🤖 End-to-End AI Pipeline

## 1. Document Ingestion

```mermaid
flowchart LR
    A[Upload Document] --> B[Validate Type + Size]
    B --> C[Hash & Duplicate Check]
    C --> D[Store Original File]
    D --> E[Extract Text]
    E --> F{Enough native text?}
    F -- Yes --> G[Keep native text]
    F -- No --> H[Tesseract OCR]
    G --> I[Chunk + Context]
    H --> I
    I --> J[Ollama Embeddings]
    J --> K[(PostgreSQL + pgvector)]
    K --> L[Document Ready]
```

### Extraction is format-aware

The extraction layer supports:

`PDF` · `DOCX` · `TXT` · `Markdown` · `CSV` · `HTML` · `JSON`

For PDFs, the system first tries **PyMuPDF native extraction**. OCR is not blindly applied to every page.

Instead, a page falls back to **Tesseract OCR only when its native text is below the configured threshold**. This keeps text PDFs fast while still supporting scanned and image-only documents.

---

## 2. Context-Aware Chunking

The project deliberately separates two ideas that are often confused:

### Physical overlap

Adjacent chunks share real boundary text so information is less likely to disappear when a sentence crosses a split.

### Rolling context summaries

Later chunks can carry a compact summary of earlier content, giving retrieval and generation more semantic continuity without duplicating the entire document history.

That creates a richer representation than simple fixed-size splitting:

```text
Document
   ↓
Page-aware extraction
   ↓
Chunk 0 ────────────────┐
   ↓ overlap             │
Chunk 1 + prior summary  │
   ↓ overlap             ├─→ semantic embedding
Chunk 2 + prior summary  │
   ↓                     │
... ─────────────────────┘
```

---

## 3. Embeddings + Vector Database

The default local embedding stack is:

```text
nomic-embed-text
        ↓
768-dimensional embedding
        ↓
PostgreSQL + pgvector
        ↓
HNSW cosine-distance index
```

Each searchable chunk stores:

- extracted text
- page number
- chunk index
- chunk hash
- rolling context summary
- vector embedding
- document ownership metadata

### Why PostgreSQL + pgvector?

Using pgvector keeps **relational application data and semantic vectors in the same database**.

That means retrieval can combine vector similarity with normal application constraints such as:

- authenticated user ownership
- document processing status
- selected document IDs
- top-k limits
- relevance score thresholds

The migration layer also adds an **HNSW index** for approximate nearest-neighbour search as the corpus grows.

---

## 4. Retrieval-Augmented Generation

```mermaid
flowchart LR
    Q[User Question] --> I[Intent + Follow-up Resolution]
    I --> QE[Query Embedding]
    QE --> VS[pgvector Similarity Search]
    VS --> T[Top Relevant Chunks]
    T --> P[Grounded Prompt]
    P --> L[Ollama llama3.2]
    L --> A[Answer + Citations]
    A --> M[Persist Conversation]
```

The LLM is **not retrained on uploaded files**.

Instead, RAG retrieves the most relevant chunks at query time and injects them into a grounded prompt. The prompt explicitly tells the model not to invent document facts when the retrieved evidence is insufficient.

That makes the project about **retrieval quality, context construction, grounding, and traceability** rather than pretending uploaded documents magically become part of the model.

---

# 🎙️ Speech-to-Text

Voice input is handled locally with **faster-whisper**.

### The STT pipeline includes

- microphone/audio upload from the Gradio UI
- local Whisper-family transcription
- CPU execution support
- `int8` compute mode
- optional language selection
- configurable beam search
- Voice Activity Detection
- audio validation and size limits
- persistent Hugging Face model caching through Docker volumes

The transcription is inserted into the composer for review before being sent as a RAG question.

This turns the system into a multimodal workflow:

```text
Voice → STT → text query → embedding → retrieval → LLM → cited answer
```

---

# 👁️ OCR for Scanned Documents

OCR is integrated into the ingestion path instead of being a separate tool.

For each PDF page:

1. PyMuPDF attempts native text extraction
2. The extracted character count is checked
3. Weak/image-only pages are rendered
4. Tesseract OCR is attempted
5. The richer result is kept
6. Page metadata records whether text came from native extraction or OCR

The code also includes a Tesseract CLI fallback when the PyMuPDF OCR path does not produce enough readable text.

This is especially useful for:

- scanned lecture notes
- image-only PDFs
- printed forms
- archived documents
- mixed PDFs containing both text and scanned pages

---

# 🧠 Local AI with Ollama

The normal application path is designed to work locally:

| AI task | Default model |
|---|---|
| 📄 Documents | PDF, DOCX, TXT, Markdown, CSV, HTML, JSON; validation, hashing, duplicate detection, page metadata |
| 👁️ OCR | PyMuPDF native extraction + selective Tesseract fallback for scanned/mixed PDFs |
| 🧩 Chunking | Page-aware chunks + physical overlap + rolling context summaries |
| 🔎 Retrieval | `nomic-embed-text` + 768-d vectors + pgvector + HNSW cosine search |
| 💬 Generation | Local `llama3.2` + grounded prompts + source citations + conversation memory |
| 🎙️ Voice | Local `faster-whisper` + VAD + CPU/`int8` support + model caching |
| 🔐 Security | PBKDF2-SHA256 + salted passwords + bearer tokens + user-scoped retrieval |
| ⚙️ Backend | Async FastAPI + SQLAlchemy + Alembic + PostgreSQL + SSE streaming |
| 🐳 Infrastructure | Docker Compose + persistent volumes + health-aware startup + GitHub Actions |

The goal is not just to make a chatbot answer questions, but to build the **complete system around the model**: reliable ingestion, retrieval quality, grounding, traceability, privacy, and reproducible infrastructure.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    U[User] --> G[Gradio Frontend :7860]
    G -->|HTTP + Bearer token| API[FastAPI Backend :8000]

    API --> AUTH[Auth + User Isolation]
    API --> DOC[Document Ingestion]
    API --> CHAT[RAG Chat]
    API --> AUDIO[Speech-to-Text]

    DOC --> EX[Format-aware Extraction]
    EX --> PDF[PyMuPDF]
    EX --> OCR[Tesseract OCR]
    DOC --> CH[Chunking + Context Summaries]
    CH --> EMB[Ollama / nomic-embed-text]
    EMB --> PG[(PostgreSQL + pgvector)]

    CHAT --> EMB
    CHAT --> PG
    CHAT --> LLM[Ollama / llama3.2]
    AUDIO --> WH[faster-whisper]
    WH --> HF[(Hugging Face Cache)]

    API --> SQLA[SQLAlchemy Async ORM]
    SQLA --> PG
    MIG[Alembic Migrations] --> PG
```

## 🤖 End-to-End AI Pipeline

```mermaid
flowchart LR
    A[Upload] --> B[Validate + Hash]
    B --> C[Store Original]
    C --> D[Extract Text]
    D --> E{Enough native text?}
    E -- Yes --> F[Keep native text]
    E -- No --> G[Tesseract OCR]
    F --> H[Chunk + Context]
    G --> H
    H --> I[Ollama Embeddings]
    I --> J[(PostgreSQL + pgvector)]
    J --> K[Query Embedding]
    K --> L[Similarity Retrieval]
    L --> M[Grounded Prompt]
    M --> N[llama3.2]
    N --> O[Answer + Citations]
```

### 📄 Ingestion & Selective OCR

Supported formats: `PDF` · `DOCX` · `TXT` · `Markdown` · `CSV` · `HTML` · `JSON`.

PDF processing uses a **two-stage extraction strategy**:

1. **PyMuPDF** first extracts native PDF text.
2. The extracted character count is checked against a configurable threshold.
3. Pages with weak or empty extraction are rendered for OCR.
4. **Tesseract** processes those pages, with a CLI fallback when needed.
5. The richer result is retained and the extraction source is recorded in metadata.

This avoids paying the OCR cost for normal text PDFs while still handling scanned and mixed documents.

### 🧩 Context-Aware Chunking

The chunker combines two different continuity mechanisms:

- **Physical overlap** preserves real text across chunk boundaries.
- **Rolling context summaries** give later chunks semantic continuity without repeatedly duplicating the entire document history.

```text
Document → page-aware extraction
          ↓
Chunk 0 ── overlap ──→ Chunk 1 + prior summary
                              ↓
                         Chunk 2 + prior summary
                              ↓
                        semantic embedding
```

This matters because chunking is not just a preprocessing step: **what information reaches the retriever directly affects RAG quality.**

### 🔎 Embeddings, pgvector & HNSW

```text
nomic-embed-text → 768-dimensional embedding
                 → PostgreSQL + pgvector
                 → HNSW cosine-distance index
```

Each searchable chunk retains extracted text, page/chunk metadata, hashes, rolling context summaries, embeddings, and document ownership. Storing vectors alongside relational data allows retrieval to combine semantic similarity with **user ownership, document status, selected documents, top-k limits, and relevance thresholds**.

### 💬 Retrieval-Augmented Generation

At query time, the system can resolve intent and follow-ups, embed the question, retrieve relevant chunks, and inject them into a grounded `llama3.2` prompt. The model is instructed not to invent document facts when evidence is insufficient, while source metadata is preserved for traceability.

**Uploaded documents are not used to retrain the LLM.** RAG supplies relevant evidence at query time through context injection.

## 🎙️ Voice Queries

```text
Voice → faster-whisper → text query → embedding → retrieval → LLM → cited answer
```

Voice input is processed locally with **faster-whisper**, supporting microphone/audio uploads, CPU execution, `int8` compute, optional language selection, configurable beam search, VAD, audio validation/size limits, and persistent Hugging Face model caching. Transcribed text is placed in the composer for review before retrieval.

## 🔐 Security & Conversation Intelligence

The application is a **multi-user document workspace**, not a global document pool.

- PBKDF2-SHA256 password hashing with random salts
- Signed bearer tokens with expiration
- Authenticated document and conversation ownership
- User-scoped vector retrieval and per-user duplicate checks
- Persistent multi-turn conversation history
- Follow-up resolution, for example, “Explain the third point” can use previous context before retrieval
- Lightweight intent routing so greetings, thanks, farewells, and calculation-like messages can bypass unnecessary retrieval
- **Server-Sent Events (SSE)** for progressive response streaming
- Source-aware results preserving filename, page, chunk index, score, and excerpts

The authenticated user is applied as a retrieval constraint **before document chunks are returned**, making isolation part of the retrieval layer rather than only a UI feature.

## 🧠 Local AI Architecture

| Task | Default model |
|---|---|
| Embeddings | `nomic-embed-text` |
| Generation | `llama3.2` |
| Speech-to-text | `faster-whisper` |

Ollama handles local embeddings and generation. The Dockerized backend reaches host Ollama through `host.docker.internal:11434`.

The application exposes practical controls for **model keep-alive, startup warmup, context-window size, maximum predicted tokens, timeouts, retrieved-context caps, summary caps, and relevance thresholds**, which are important when running local models on constrained hardware. A provider abstraction also supports OpenAI for embeddings and/or generation.

## 🐳 Docker & Infrastructure

Docker is part of the system design rather than just packaging.

| Service | Purpose | Port |
|---|---|---:|
| `postgres` | PostgreSQL + pgvector | `5432` |
| `backend` | FastAPI application | `8000` |
| `frontend` | Gradio interface | `7860` |
| Ollama | Local models on host | `11434` |

Compose provides service discovery (`postgres:5432`), while the backend reaches host Ollama through `host.docker.internal`. Named volumes persist **database/vector state, uploaded documents, and Whisper model cache**. Health checks make the backend wait for PostgreSQL and the frontend depend on backend readiness.

## 💡 Key Engineering Decisions

| Decision | Why |
|---|---|
| **Selective OCR** | Avoid expensive OCR when native PDF text is already usable |
| **Physical overlap + rolling summaries** | Preserve boundary text while maintaining semantic continuity |
| **PostgreSQL + pgvector** | Combine vector search with relational application constraints |
| **HNSW** | Efficient approximate nearest-neighbor retrieval as the corpus grows |
| **Local Ollama** | Keep documents, embeddings, and generation local and controllable |
| **SSE streaming** | Return generated responses progressively instead of waiting for completion |
| **User-scoped retrieval** | Prevent cross-user document leakage at the retrieval layer |
| **Provider abstraction** | Support local inference while retaining an OpenAI path |

## 📊 RAG Evaluation

The project includes `scripts/evaluate_rag.py` with a small retrieval evaluation dataset. It checks whether expected context is actually retrieved for known questions, giving the system an explicit way to assess **retrieval quality** rather than judging it only by whether the LLM produced an answer.

```text
Question
   ↓
Retriever
   ↓
Retrieved chunks
   ↓
Expected context retrieved?
   ↓
Retrieval evaluation
```

## 📚 Further Documentation

The README gives the high-level picture. The repository also includes focused documentation for readers who want to go deeper:

- [🏗️ Architecture](docs/ARCHITECTURE.md) - detailed backend, frontend, database, service, and deployment architecture
- [🤖 AI Pipeline](docs/AI_PIPELINE.md) - deeper explanation of ingestion, OCR, chunking, embeddings, retrieval, and generation
- [🧪 Testing & Evaluation](docs/TESTING_AND_EVALUATION.md) - testing strategy, security coverage, E2E workflows, and RAG evaluation
- [📖 Learning Notes](docs/LEARNING_NOTES.md) - deeper technical notes and concepts explored while building the system

## 🧰 Technology Stack

| Layer | Technology | Role |
|---|---|---|
| Language | **Python 3.12** | Core application and AI pipeline |
| Frontend / API | **Gradio / FastAPI** | UI, typed async REST API, OpenAPI |
| Database | **PostgreSQL + pgvector** | Relational + semantic storage |
| ORM / Migrations | **SQLAlchemy Async / Alembic** | Persistence and schema evolution |
| LLM / Embeddings | **Ollama / llama3.2 / nomic-embed-text** | Local generation and embeddings |
| OCR / Extraction | **Tesseract / PyMuPDF / python-docx / pandas / BeautifulSoup** | Document processing |
| STT | **faster-whisper** | Local voice transcription |
| HTTP | **httpx** | Async service/provider communication |
| Containers | **Docker + Docker Compose** | Reproducible services |
| Testing | **pytest / pytest-asyncio** | Unit, integration, security, E2E |
| Quality / CI | **Ruff / mypy / GitHub Actions** | Code quality and automated checks |

## 🧪 Testing & Quality

Testing covers **API behavior, authentication, security boundaries, chunking, embeddings, extraction/OCR, context features, pgvector retrieval, and end-to-end RAG workflows**.

```bash
pytest
ruff check .
ruff format --check .
mypy backend frontend
```

## 🚀 Getting Started

### Prerequisites

Install **Docker Desktop + Compose**, **Ollama**, and Git. Tesseract is installed in the backend image.

### 1. Clone and configure

```bash
git clone <YOUR_REPOSITORY_URL>
cd RAG-Document-Assistant
cp .env.example .env
```

On Windows Command Prompt:

```bat
copy .env.example .env
```

Set at minimum:

```env
AUTH_SECRET_KEY=replace_with_a_long_random_secret
POSTGRES_PASSWORD=replace_with_a_database_password
```

Generate a strong secret with `openssl rand -hex 32` and never commit the real `.env`.

### 2. Pull models and start

```bash
ollama pull llama3.2
ollama pull nomic-embed-text

docker compose up --build -d
docker compose ps
```

### 3. Open the application

| Service | URL |
|---|---|
| Gradio | `http://127.0.0.1:7860` |
| FastAPI docs | `http://127.0.0.1:8000/docs` |
| API health | `http://127.0.0.1:8000/api/v1/health` |
| API readiness | `http://127.0.0.1:8000/api/v1/ready` |

Stop with `docker compose down`.

> Avoid `docker compose down -v` unless you intentionally want to delete PostgreSQL data, uploaded documents, and cached Whisper models.

## 📁 Repository Structure

```text
RAG-Document-Assistant/
├── backend/
│   ├── app/
│   │   ├── api/endpoints/        # auth, documents, chat, search, audio, health
│   │   ├── core/                 # security, logging, exceptions
│   │   ├── models/               # SQLAlchemy models
│   │   ├── schemas/              # typed API contracts
│   │   └── services/             # RAG, OCR, STT, storage, retrieval, LLM
│   ├── migrations/               # Alembic + pgvector/HNSW migrations
│   └── Dockerfile
├── frontend/                     # Gradio workspace
├── scripts/                      # evaluation dataset + RAG evaluator
├── docs/                         # architecture, AI pipeline, testing notes
├── tests/                        # automated test suite
├── docker-compose.yml
├── .env.example
├── pyproject.toml
└── README.md
```

## 📌 What This Project Demonstrates

A production-oriented RAG system is more than an LLM call. This project combines **document processing, selective OCR, context-aware chunking, vector search, grounded generation, speech-to-text, authentication, multi-user isolation, async APIs, database migrations, Docker, testing, retrieval evaluation, and CI** into one reproducible application.

The emphasis is on **building the complete system around the model**, not just connecting an LLM to a document upload button.
