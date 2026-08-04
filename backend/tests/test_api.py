import io
import uuid
from fastapi.testclient import TestClient
import pytest
from backend.app.core.security import create_access_token
from backend.app.main import app

client = TestClient(app)


def test_readiness_endpoint():
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "vector_db" in data


def test_upload_and_list_documents_api():
    user_id = str(uuid.uuid4())
    token = create_access_token(user_id)
    headers = {"Authorization": f"Bearer {token}"}

    file_content = b"Sample text content for testing FastAPI document upload endpoint."
    files = {"file": ("test_doc.txt", io.BytesIO(file_content), "text/plain")}
    data = {"user_id": user_id}

    # Test Upload
    response = client.post("/api/v1/documents/upload", files=files, data=data, headers=headers)
    assert response.status_code == 201
    doc_data = response.json()
    assert doc_data["filename"] == "test_doc.txt"
    assert doc_data["status"] == "ready"
    doc_id = doc_data["id"]

    # Test List Documents
    list_res = client.get("/api/v1/documents", params={"user_id": user_id}, headers=headers)
    assert list_res.status_code == 200
    docs_list = list_res.json()
    assert len(docs_list) >= 1
    assert any(d["id"] == doc_id for d in docs_list)

    # Test Document Status
    status_res = client.get(f"/api/v1/documents/{doc_id}/status")
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "ready"

    # Test Search Endpoint
    search_payload = {
        "user_id": user_id,
        "query": "FastAPI document upload",
        "limit": 5,
    }
    search_res = client.post("/api/v1/search", json=search_payload, headers=headers)
    assert search_res.status_code == 200
    assert "results" in search_res.json()

    # Test Chat Endpoint
    chat_payload = {
        "user_id": user_id,
        "message": "What is in the document?",
        "top_k": 3,
    }
    chat_res = client.post("/api/v1/chat", json=chat_payload, headers=headers)
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert "answer" in chat_data
    assert "conversation_id" in chat_data
