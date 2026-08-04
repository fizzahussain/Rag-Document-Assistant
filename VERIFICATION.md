# Local verification

From Git Bash in the repository root:

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev]"
ruff format .
ruff check .
python -m compileall backend frontend scripts
pytest -q
mypy backend frontend
```

For Docker:

```bash
cp .env.example .env
# Set a long random AUTH_SECRET_KEY in .env
TOKEN=$(python scripts/create_dev_token.py)
# Put TOKEN into RAG_ACCESS_TOKEN in .env
docker compose config
docker compose build
docker compose up -d
docker compose ps
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/ready
```

The backend now requires `Authorization: Bearer <token>` for document, search, chat, and conversation endpoints.
