FROM python:3.12-slim

WORKDIR /app

COPY frontend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY frontend/ /app/frontend/

EXPOSE 7860

ENV BACKEND_URL=http://backend:8000/api/v1

CMD ["python", "frontend/app.py"]
