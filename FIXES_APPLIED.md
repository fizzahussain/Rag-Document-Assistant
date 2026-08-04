# Fixes applied

## Security

- Removed client-controlled user IDs from upload, list, search, chat, reprocess, delete, and conversation APIs
- Removed `X-User-ID` and silent development-user authentication fallbacks
- Added bearer-token-only identity resolution with generic authentication errors
- Added ownership scoping to documents, chunks, conversations, messages, search filters, and deletion
- Removed storage paths, file hashes, and owner IDs from document API responses
- Added cross-user isolation tests

## Persistence and lifecycle

- Removed silent PostgreSQL-to-SQLite runtime fallback
- Removed automatic schema creation during application startup
- Kept Alembic as the schema migration mechanism
- Added database and Qdrant shutdown handling
- Added real readiness checks that return HTTP 503 when dependencies are unavailable

## Uploads and storage

- Changed uploads to bounded streaming rather than reading the entire request into memory
- Added size enforcement while streaming, empty-file rejection, SHA-256 calculation, temporary files, atomic rename, and partial-file cleanup
- Added basic content validation for PDF, DOCX, and JSON
- Preserved user-isolated storage directories and path traversal checks

## Ingestion and retrieval

- Added stable document-specific chunk identifiers
- Replaced old chunks instead of merely selecting them during reprocessing
- Added database uniqueness constraints for chunk index and hash per document
- Removed authoritative chunk text from Qdrant payloads
- Hydrated retrieved text from PostgreSQL after user-scoped Qdrant search
- Added stale-point rejection and document ownership validation
- Added idempotent reprocessing tests

## Frontend

- Removed editable user UUID controls
- Added token-based backend calls
- Removed user IDs from query strings and JSON request bodies
- Added centralized HTTP timeout and error handling

## Infrastructure

- Added non-root Docker images
- Pinned PostgreSQL and Qdrant image versions
- Added `.dockerignore`
- Added Alembic migration entrypoint
- Removed public PostgreSQL and Qdrant host ports from Compose
- Added required `AUTH_SECRET_KEY` configuration
- Added a local development token generation script

## Verification performed here

- All Python files passed `compileall`
- `pyproject.toml` parsed successfully
- `docker-compose.yml` parsed successfully
- No remaining client-supplied identity patterns were found in application or frontend code
- No silent SQLite or in-memory Qdrant fallback strings remain
- No common dangerous Python execution patterns were found

## Verification limitation

The sandbox did not have Ruff or `aiosqlite`, and network access was unavailable, so dependencies could not be installed and the full pytest/Ruff/mypy/Docker suite could not be executed here. Run the commands in `VERIFICATION.md` in your local virtual environment before merging.
