#!/bin/sh
set -eu
alembic -c backend/alembic.ini upgrade head
exec uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
