# Production Multi-User RAG System

A production-grade, multi-user Document Ingestion and Retrieval-Augmented Generation (RAG) system built from scratch using Python 3.12, FastAPI, Gradio, SQLAlchemy 2.0 Async, PostgreSQL, and Qdrant.

---

## Architecture Overview

```text
               +----------------------------------+
               |         Gradio Dashboard        |
               |      (HTTP API Client UI)        |
               +----------------------------------+
                                |
                                v
               +----------------------------------+
               |          FastAPI Backend         |
               |             (/api/v1)            |
               +----------------------------------+
                   /           |            \
                  /            |             \
                 v             v              v
     +---------------+  +--------------+  +-------------------+
     | Local Storage |  |  PostgreSQL  |  |   Qdrant Vector   |
     | (Safe Paths,  |  | (Source of   |  |   Database        |
     |  SHA-256)     |  |  Truth DB)   |  |  (Derived Index)  |
     +---------------+  +--------------+  +-------------------+
```

### PostgreSQL (Source of Truth)
Stores users, documents, original metadata, file hashes, processing statuses, page records, chunk metadata, conversations, messages, and audit error logs.

### Qdrant (Derived Index)
Stores chunk vector embeddings and payload metadata (document_id, chunk_id, user_id, page_number, filename, content_hash). It can be completely rebuilt at any time from PostgreSQL.

---

## Features

- **Multi-User Isolation**: User-level document isolation enforced via PostgreSQL foreign keys and Qdrant payload filters.
- **Idempotent Ingestion Pipeline**: Processing lifecycle validation (`pending` -> `uploaded` -> `queued` -> `extracting` -> `extracted` -> `chunking` -> `embedding` -> `indexing` -> `ready`). Retrying or uploading the same file hash updates records without duplicating chunks.
- **Extensible File Extractors**: Native support for **PDF**, **DOCX**, **TXT**, **Markdown**, **CSV**, **HTML**, and **JSON**.
- **Scanned PDF Detection**: Automatically detects image-only/scanned PDFs with little or no extractable text and flags an `OCRRequiredError`.
- **Custom Text Chunker**: Token/character-aware sliding window chunker with overlapping boundaries, page numbers, and SHA-256 chunk hashes.
- **Configurable Embeddings & LLM**: Supports deterministic mock providers (for zero-cost offline testing without API keys) and OpenAI API (`text-embedding-3-small` & `gpt-4o-mini`).
- **Citation Tracking**: Returns answers grounded strictly in document context with stable references `[filename, page N]`.
- **Gradio Dashboard**: Modular UI for uploading, inspecting processing status, selecting target documents, chatting, and reviewing retrieved source excerpts.

---

## Quickstart with Docker Compose

To launch the complete infrastructure (PostgreSQL, Qdrant, FastAPI backend, and Gradio frontend):

```bash
# 1. Clone or navigate to repository root
cd RAG

# 2. Copy environment configuration
cp .env.example .env

# 3. Build and launch services
docker-compose up --build
```

Access the interfaces:
- **Gradio UI**: [http://localhost:7860](http://localhost:7860)
- **FastAPI OpenAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Qdrant Dashboard**: [http://localhost:6333/dashboard](http://localhost:6333/dashboard)

---

## Local Development & Testing Setup

### 1. Installation
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt
pip install -r frontend/requirements.txt
```

### 2. Run Database Migrations (PostgreSQL)
```bash
cd backend
alembic upgrade head
```

### 3. Run Test Suite
```bash
# Run all unit, API, vector, and end-to-end RAG tests
python -m pytest
```

### 4. Run RAG Evaluation Benchmark
```bash
python -m scripts.evaluate_rag
```

---

## API Endpoints Reference

All endpoints are versioned under `/api/v1`:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/health` | Service health status for DB & Qdrant |
| `GET` | `/api/v1/ready` | Readiness probe |
| `POST` | `/api/v1/documents/upload` | Upload & ingest document |
| `GET` | `/api/v1/documents` | List user documents |
| `GET` | `/api/v1/documents/{id}` | Get document metadata |
| `GET` | `/api/v1/documents/{id}/status` | Check processing status |
| `GET` | `/api/v1/documents/{id}/chunks` | List extracted document chunks |
| `POST` | `/api/v1/documents/{id}/reprocess` | Reprocess document idempotently |
| `DELETE` | `/api/v1/documents/{id}` | Delete document from DB, disk, and Qdrant |
| `POST` | `/api/v1/search` | Execute semantic vector search |
| `POST` | `/api/v1/chat` | RAG Chat generation with citations |
| `GET` | `/api/v1/conversations` | List user conversations |
| `DELETE` | `/api/v1/conversations/{id}` | Delete conversation history |

---

## Security Checklist

- [x] **Path Traversal Prevention**: Sanitizes all filenames and resolves paths against base upload directory.
- [x] **File Validation**: Strict file extension, MIME-type, and size validation prior to processing.
- [x] **SHA-256 Hashing**: Prevents file collision and duplicate ingestions.
- [x] **Qdrant Payload Filtering**: Enforces `user_id` filters on every vector query.
- [x] **Untrusted Context Handling**: Prompt templates treat retrieved document text strictly as untrusted context, preventing prompt injection attacks.
- [x] **CORS Configuration**: Restricts backend API origins to configured frontend domains.
