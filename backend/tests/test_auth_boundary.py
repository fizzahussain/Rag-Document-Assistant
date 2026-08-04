import uuid

from fastapi.testclient import TestClient

from backend.app.core.security import create_access_token


def test_missing_token_is_rejected(client: TestClient) -> None:
    assert client.get("/api/v1/documents").status_code == 401


def test_x_user_id_cannot_authenticate(client: TestClient) -> None:
    response = client.get(
        "/api/v1/documents",
        headers={"X-User-ID": str(uuid.uuid4())},
    )
    assert response.status_code == 401


def test_expired_token_is_rejected(client: TestClient) -> None:
    token = create_access_token(str(uuid.uuid4()), expires_in=-1)
    response = client.get(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


def test_client_user_id_is_not_accepted_by_search(client: TestClient) -> None:
    user_id = uuid.uuid4()
    token = create_access_token(str(user_id))
    response = client.post(
        "/api/v1/search",
        json={"query": "hello", "user_id": str(uuid.uuid4())},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["results"] == []
