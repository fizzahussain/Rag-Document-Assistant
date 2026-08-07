FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN addgroup --system app && adduser --system --ingroup app app
COPY pyproject.toml README.md ./
COPY backend ./backend
COPY frontend ./frontend
RUN pip install --no-cache-dir .
RUN chown -R app:app /app
USER app
EXPOSE 7860
CMD ["python", "frontend/app.py"]
