"""
Studable API — Health endpoint tests.

These tests run WITHOUT a live PostgreSQL connection.
The database check is mocked so the full CI pipeline can pass on any machine.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

# ── Shared test client ────────────────────────────────────────────────────────
client = TestClient(app)


# ── Application metadata ──────────────────────────────────────────────────────
class TestAppMetadata:
    def test_app_title(self):
        """The FastAPI application must carry the correct product name."""
        assert app.title == "Studable API"

    def test_app_version(self):
        """Version must follow semantic versioning starting at 1.0.0."""
        assert app.version == "1.0.0"


# ── Root endpoint ─────────────────────────────────────────────────────────────
class TestRootEndpoint:
    def test_root_returns_200(self):
        response = client.get("/")
        assert response.status_code == 200

    def test_root_message(self):
        response = client.get("/")
        assert response.json()["message"] == "Studable API is running"

    def test_root_has_docs_link(self):
        response = client.get("/")
        assert response.json()["docs"] == "/docs"


# ── Health endpoint — database connected ──────────────────────────────────────
class TestHealthEndpointConnected:
    def test_status_code(self):
        with patch("app.api.routes.health.check_db_connection", return_value=True):
            response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_status_field(self):
        with patch("app.api.routes.health.check_db_connection", return_value=True):
            response = client.get("/api/v1/health")
        assert response.json()["status"] == "healthy"

    def test_service_field(self):
        with patch("app.api.routes.health.check_db_connection", return_value=True):
            response = client.get("/api/v1/health")
        assert response.json()["service"] == "Studable API"

    def test_database_connected(self):
        with patch("app.api.routes.health.check_db_connection", return_value=True):
            response = client.get("/api/v1/health")
        assert response.json()["database"] == "connected"


# ── Health endpoint — database unavailable ────────────────────────────────────
class TestHealthEndpointDbUnavailable:
    def test_still_returns_200(self):
        """App stays up even when DB is unreachable."""
        with patch("app.api.routes.health.check_db_connection", return_value=False):
            response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_status_still_healthy(self):
        with patch("app.api.routes.health.check_db_connection", return_value=False):
            response = client.get("/api/v1/health")
        assert response.json()["status"] == "healthy"

    def test_database_unavailable(self):
        with patch("app.api.routes.health.check_db_connection", return_value=False):
            response = client.get("/api/v1/health")
        assert response.json()["database"] == "unavailable"


# ── API documentation ─────────────────────────────────────────────────────────
class TestApiDocumentation:
    def test_swagger_ui_accessible(self):
        response = client.get("/docs")
        assert response.status_code == 200

    def test_redoc_accessible(self):
        response = client.get("/redoc")
        assert response.status_code == 200

    def test_openapi_schema_accessible(self):
        response = client.get("/openapi.json")
        assert response.status_code == 200

    def test_openapi_schema_has_correct_title(self):
        response = client.get("/openapi.json")
        schema = response.json()
        assert schema["info"]["title"] == "Studable API"

    def test_health_route_in_schema(self):
        response = client.get("/openapi.json")
        paths = response.json()["paths"]
        assert "/api/v1/health" in paths
