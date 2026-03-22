"""Tests for authentication utilities."""
import pytest
from datetime import timedelta
from unittest.mock import patch
from jose import jwt


class TestAccessToken:
    """Test JWT token creation and validation."""

    def test_create_token_returns_string(self):
        from app.api.deps import create_access_token
        token = create_access_token("user-123")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_contains_user_id(self):
        from app.api.deps import create_access_token
        from app.core.config import settings
        token = create_access_token("user-abc")
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["sub"] == "user-abc"

    def test_token_has_expiry(self):
        from app.api.deps import create_access_token
        from app.core.config import settings
        token = create_access_token("user-123")
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert "exp" in payload

    def test_custom_expiry_delta(self):
        from app.api.deps import create_access_token
        from app.core.config import settings
        token = create_access_token("user-123", expires_delta=timedelta(minutes=5))
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert "exp" in payload

    def test_different_users_get_different_tokens(self):
        from app.api.deps import create_access_token
        token1 = create_access_token("user-1")
        token2 = create_access_token("user-2")
        assert token1 != token2
