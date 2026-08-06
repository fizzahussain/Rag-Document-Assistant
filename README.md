# Document Assistant

A clean multi-user RAG application with a Gradio frontend, FastAPI backend, PostgreSQL + pgvector, and local Ollama models.

## Features

- Sign up, login, and logout
- Private documents and chats per user
- PDF, DOCX, TXT, Markdown, CSV, HTML, and JSON ingestion
- PostgreSQL vector search with pgvector
- Local embeddings and answers through Ollama
- Simple two-column Gradio interface
- Source references for generated answers

## Run locally on Windows

1. Copy the environment file:

```bash
cp .env.example .env
```

2. Set a long `AUTH_SECRET_KEY` in `.env`.

3. Install and prepare Ollama:

```bash
ollama pull nomic-embed-text
ollama pull llama3.2
```

4. Start PostgreSQL:

```bash
docker compose up -d postgres
```

5. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r backend/requirements.txt
pip install -r frontend/requirements.txt
```

6. Apply migrations:

```bash
alembic -c backend/alembic.ini upgrade head
```

7. Start FastAPI in one terminal:

```bash
uvicorn backend.app.main:app --reload
```

8. Start Gradio in a second terminal:

```bash
source .venv/Scripts/activate
python frontend/app.py
```

9. Open `http://127.0.0.1:7860`, create an account, upload documents, and chat.

## Docker

With Ollama running on the host:

```bash
docker compose up --build
```

Open `http://127.0.0.1:7860`.

## Tests

```bash
pytest backend/tests
```
