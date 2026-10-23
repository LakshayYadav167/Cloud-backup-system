"""Pytest configuration and shared test fixtures."""

import pytest
from app.main import app

try:
    from fastapi.testclient import TestClient

    @pytest.fixture(scope="session")
    def client():
        """Reusable TestClient fixture for API integration tests."""
        with TestClient(app) as test_client:
            yield test_client
except ImportError:
    pass
