import io

from fastapi.testclient import TestClient


def signup_headers(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/signup",
        json={"name": "Test User", "email": email, "password": "password123"},
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_readiness_endpoint(client: TestClient) -> None:
    response = client.get("/api/v1/ready")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "healthy"


def test_protected_endpoint_requires_token(client: TestClient) -> None:
    response = client.get("/api/v1/documents")
    assert response.status_code == 401


def test_upload_search_chat_and_user_isolation(client: TestClient) -> None:
    headers_a = signup_headers(client, "user-a@example.com")
    headers_b = signup_headers(client, "user-b@example.com")
    response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "test_doc.txt",
                io.BytesIO(b"FastAPI supports document upload and retrieval testing."),
                "text/plain",
            )
        },
        headers=headers_a,
    )
    assert response.status_code == 201, response.text
    document = response.json()
    document_id = document["id"]

    own_list = client.get("/api/v1/documents", headers=headers_a)
    assert own_list.status_code == 200
    assert any(item["id"] == document_id for item in own_list.json())

    other_list = client.get("/api/v1/documents", headers=headers_b)
    assert other_list.status_code == 200
    assert all(item["id"] != document_id for item in other_list.json())

    forbidden_detail = client.get(f"/api/v1/documents/{document_id}", headers=headers_b)
    assert forbidden_detail.status_code == 404

    search = client.post(
        "/api/v1/search",
        json={"query": "FastAPI document upload", "limit": 5},
        headers=headers_a,
    )
    assert search.status_code == 200, search.text
    assert search.json()["results"]

    other_search = client.post(
        "/api/v1/search",
        json={"query": "FastAPI document upload", "limit": 5},
        headers=headers_b,
    )
    assert other_search.status_code == 200
    assert other_search.json()["results"] == []

    chat = client.post(
        "/api/v1/chat",
        json={"message": "What does the document discuss?", "top_k": 3},
        headers=headers_a,
    )
    assert chat.status_code == 200, chat.text
    assert chat.json()["retrieved_sources"]

    first_chunks = client.get(
        f"/api/v1/documents/{document_id}/chunks",
        headers=headers_a,
    ).json()
    reprocess = client.post(
        f"/api/v1/documents/{document_id}/reprocess",
        headers=headers_a,
    )
    assert reprocess.status_code == 200, reprocess.text
    second_chunks = client.get(
        f"/api/v1/documents/{document_id}/chunks",
        headers=headers_a,
    ).json()
    assert [item["id"] for item in first_chunks] == [item["id"] for item in second_chunks]

    delete_other = client.delete(f"/api/v1/documents/{document_id}", headers=headers_b)
    assert delete_other.status_code == 404

    delete_own = client.delete(f"/api/v1/documents/{document_id}", headers=headers_a)
    assert delete_own.status_code == 204
