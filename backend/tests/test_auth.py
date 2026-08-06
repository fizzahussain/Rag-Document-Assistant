from fastapi.testclient import TestClient


def test_signup_login_and_me(client: TestClient) -> None:
    signup = client.post(
        "/api/v1/auth/signup",
        json={"name": "Test User", "email": "test@example.com", "password": "password123"},
    )
    assert signup.status_code == 201, signup.text
    token = signup.json()["access_token"]

    duplicate = client.post(
        "/api/v1/auth/signup",
        json={"name": "Other", "email": "TEST@example.com", "password": "password123"},
    )
    assert duplicate.status_code == 409

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "password123"},
    )
    assert login.status_code == 200

    wrong = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "wrong-password"},
    )
    assert wrong.status_code == 401

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == "test@example.com"
