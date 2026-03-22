"""Tests for the health and root endpoints."""
import pytest
from unittest.mock import patch, MagicMock


def _get_test_client():
    """Create a TestClient with mocked database dependencies."""
    # Mock the settings to avoid requiring a real .env file
    with patch("app.core.config.Settings") as MockSettings:
        mock_settings = MagicMock()
        mock_settings.APP_NAME = "DocBrain"
        mock_settings.CORS_ORIGIN_LIST = ["http://localhost:5173"]
        mock_settings.RATE_LIMIT_PER_MINUTE = 120
        mock_settings.ENVIRONMENT = "test"

        with patch("app.core.config.settings", mock_settings):
            with patch("app.main.settings", mock_settings):
                from fastapi.testclient import TestClient
                from app.main import app
                return TestClient(app)


# We create the client once; if imports fail due to missing .env
# the tests are simply skipped.
try:
    client = _get_test_client()
    _skip = False
except Exception:
    client = None
    _skip = True

skipif_no_client = pytest.mark.skipif(_skip, reason="Could not create test client (missing .env or deps)")


@skipif_no_client
class TestHealthEndpoint:
    def test_health_returns_200(self):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_body(self):
        data = client.get("/health").json()
        assert data["status"] == "healthy"
        assert "service" in data
        assert "version" in data

    def test_root_returns_200(self):
        response = client.get("/")
        assert response.status_code == 200
        assert "message" in response.json()
