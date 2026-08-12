# 🧪 Testing & Evaluation

## Test Suite

The backend test suite includes coverage for:

- API endpoints
- registration/login
- authentication boundary cases
- chunking
- embeddings
- extraction
- OCR-related behavior
- context features
- pgvector retrieval
- end-to-end RAG flows

Pytest markers define:

- `unit`
- `integration`
- `e2e`
- `security`

## Run Tests

```bash
pytest
```

For coverage:

```bash
pytest --cov=backend --cov-report=term-missing
```

## Static Quality Checks

```bash
ruff check .
ruff format --check .
mypy backend frontend
```

## Retrieval Evaluation

The repository includes:

```text
scripts/eval_dataset.json
scripts/evaluate_rag.py
```

The evaluation script builds a controlled document, retrieves the top results for each query, checks expected context keywords, and reports a retrieval hit rate.

It uses mock embedding/LLM providers so the evaluation path can focus on retrieval behavior without requiring a live paid model provider.

## CI / Repository Hygiene

The GitHub Actions workflow checks repository hygiene, including:

- required governance files
- accidental `.env` commits
- private key files
- YAML validity

This is especially useful for an AI project because environment files frequently contain provider keys, database credentials, and application secrets.
