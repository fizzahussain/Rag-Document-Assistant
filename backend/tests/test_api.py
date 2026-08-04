import io
import uuid

from fastapi.testclient import TestClient

from backend.app.core.security import create_access_token


def test_readiness_endpoint(client: TestClient) -> None:
    """Check that the readiness endpoint responds successfully"""

    response = client.get("/api/v1/ready")

    assert response.status_code == 200, response.text
    assert response.json() == {"status": "ready"}


def test_health_endpoint(client: TestClient) -> None:
    """Check that the health endpoint reports dependency status"""

    response = client.get("/api/v1/health")

    assert response.status_code == 200, response.text

    data = response.json()

    assert "status" in data
    assert "database" in data
    assert "vector_db" in data


def test_upload_and_list_documents_api(client: TestClient) -> None:
    """Exercise the main document upload and RAG API workflow"""

    user_id = str(uuid.uuid4())
    token = create_access_token(user_id)

    headers = {
        "Authorization": f"Bearer {token}",
    }

    file_content = b"Sample text content for testing FastAPI document upload endpoint."

    files = {
        "file": (
            "test_doc.txt",
            io.BytesIO(file_content),
            "text/plain",
        )
    }

    data = {
        "user_id": user_id,
    }

    # Upload document
    response = client.post(
        "/api/v1/documents/upload",
        files=files,
        data=data,
        headers=headers,
    )

    assert response.status_code == 201, response.text

    document_data = response.json()

    assert document_data["filename"] == "test_doc.txt"
    assert document_data["status"] == "ready"

    document_id = document_data["id"]

    # List documents
    list_response = client.get(
        "/api/v1/documents",
        params={"user_id": user_id},
        headers=headers,
    )

    assert list_response.status_code == 200, list_response.text

    documents = list_response.json()

    assert len(documents) >= 1
    assert any(document["id"] == document_id for document in documents)

    # Check document status
    status_response = client.get(
        f"/api/v1/documents/{document_id}/status",
        headers=headers,
    )

    assert status_response.status_code == 200, status_response.text
    assert status_response.json()["status"] == "ready"

    # Search uploaded document
    search_payload = {
        "user_id": user_id,
        "query": "FastAPI document upload",
        "limit": 5,
    }

    search_response = client.post(
        "/api/v1/search",
        json=search_payload,
        headers=headers,
    )

    assert search_response.status_code == 200, search_response.text

    search_data = search_response.json()

    assert "results" in search_data
    assert isinstance(search_data["results"], list)

    # Ask a document-grounded question
    chat_payload = {
        "user_id": user_id,
        "message": "What is in the document?",
        "top_k": 3,
    }

    chat_response = client.post(
        "/api/v1/chat",
        json=chat_payload,
        headers=headers,
    )

    assert chat_response.status_code == 200, chat_response.text

    chat_data = chat_response.json()

    assert "answer" in chat_data
    assert "conversation_id" in chat_data
    assert chat_data["answer"]
