"""Unit tests for the health check and root endpoints."""

from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    """Verify that the root endpoint returns 200 OK and valid metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "project" in data
    assert "docs_url" in data
    assert data["docs_url"] == "/docs"
    assert "api_v1_endpoints" in data


def test_health_check_endpoint(client: TestClient):
    """Verify that /api/v1/health reports healthy status and storage provider."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database_status"] == "connected"
    assert "storage_provider" in data
    assert "timestamp" in data
    assert "version" in data
