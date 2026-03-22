"""Tests for the health and root endpoints using a real TestClient."""

import sys
from unittest.mock import MagicMock

# Mock heavy dependencies so we can import app.main without ML libraries.
_MOCKED_MODULES = [
    "aiofiles",
    "celery",
    "celery.result",
    "pinecone",
    "PyPDF2",
    "markdown",
    "PIL",
    "PIL.Image",
    "pytesseract",
    "docling",
    "docling.document_converter",
    "docling.datamodel",
    "docling.datamodel.base_models",
    "docling.datamodel.pipeline_options",
    "torch",
    "sentence_transformers",
    "FlagEmbedding",
    "sendgrid",
    "sendgrid.helpers",
    "sendgrid.helpers.mail",
    "google.generativeai",
    "google.genai",
    "openai",
    "anthropic",
    "dirtyjson",
]

for _mod in _MOCKED_MODULES:
    sys.modules.setdefault(_mod, MagicMock())

# pymysql shim so SQLAlchemy can resolve the mysql dialect
try:
    import pymysql

    pymysql.install_as_MySQLdb()
except ImportError:
    sys.modules.setdefault("MySQLdb", MagicMock())

from fastapi.testclient import TestClient

from app.main import app  # noqa: E402 — must come after mocks

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_200(self):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_has_status(self):
        data = client.get("/health").json()
        assert data["status"] == "healthy"

    def test_health_response_has_service_name(self):
        data = client.get("/health").json()
        assert data["service"] == "DocBrain"

    def test_health_response_has_version(self):
        data = client.get("/health").json()
        assert "version" in data


class TestRootEndpoint:
    def test_root_returns_200(self):
        response = client.get("/")
        assert response.status_code == 200

    def test_root_has_message(self):
        data = client.get("/").json()
        assert "message" in data
        assert "DocBrain" in data["message"]


class TestAppRoutes:
    def test_health_route_exists(self):
        routes = [r.path for r in app.routes]
        assert "/health" in routes

    def test_auth_routes_exist(self):
        routes = [r.path for r in app.routes]
        assert "/auth/token" in routes

    def test_knowledge_base_routes_exist(self):
        routes = [r.path for r in app.routes]
        assert any(r.startswith("/knowledge-bases") for r in routes)
