from fastapi.testclient import TestClient
import pytest
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
