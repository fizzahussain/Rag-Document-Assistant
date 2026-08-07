FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng && rm -rf /var/lib/apt/lists/*
RUN addgroup --system app && adduser --system --ingroup app app
COPY pyproject.toml README.md ./
COPY backend ./backend
COPY frontend ./frontend
RUN pip install --no-cache-dir .
RUN mkdir -p /app/data/uploads && chown -R app:app /app
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')"
ENTRYPOINT ["/app/backend/entrypoint.sh"]
