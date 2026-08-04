import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

# These variables must be set before the application is imported
os.environ["APP_ENV"] = "test"
os.environ["QDRANT_HOST"] = ":memory:"

from backend.app.main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create a FastAPI test client"""

    with TestClient(app) as test_client:
        yield test_client
