import io

from fastapi.testclient import TestClient


def test_document_lifecycle_is_idempotent_and_isolated(client: TestClient) -> None:
    signup = client.post(
        "/api/v1/auth/signup",
        json={"name": "E2E User", "email": "e2e@example.com", "password": "password123"},
    )
    assert signup.status_code == 201, signup.text
    headers = {"Authorization": f"Bearer {signup.json()['access_token']}"}
    upload = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "fastapi.txt",
                io.BytesIO(b"FastAPI is a modern Python framework for building APIs."),
                "text/plain",
            )
        },
        headers=headers,
    )
    assert upload.status_code == 201, upload.text
    document_id = upload.json()["id"]

    chunks_before = client.get(
        f"/api/v1/documents/{document_id}/chunks",
        headers=headers,
    ).json()
    assert chunks_before

    reprocess = client.post(
        f"/api/v1/documents/{document_id}/reprocess",
        headers=headers,
    )
    assert reprocess.status_code == 200, reprocess.text
    chunks_after = client.get(
        f"/api/v1/documents/{document_id}/chunks",
        headers=headers,
    ).json()
    assert [item["id"] for item in chunks_before] == [item["id"] for item in chunks_after]

    answer = client.post(
        "/api/v1/chat",
        json={"message": "What is FastAPI?", "document_ids": [document_id]},
        headers=headers,
    )
    assert answer.status_code == 200, answer.text
    assert answer.json()["retrieved_sources"]

    deleted = client.delete(f"/api/v1/documents/{document_id}", headers=headers)
    assert deleted.status_code == 204
    missing = client.get(f"/api/v1/documents/{document_id}", headers=headers)
    assert missing.status_code == 404
