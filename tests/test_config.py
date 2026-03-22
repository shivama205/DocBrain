"""Tests for configuration and settings."""


class TestCORSConfig:
    """Test CORS origin parsing."""

    def test_default_cors_origins(self):
        from app.core.config import settings

        origins = settings.CORS_ORIGIN_LIST
        assert isinstance(origins, list)
        assert len(origins) >= 1
        # Should not contain wildcard
        assert "*" not in origins

    def test_cors_origins_are_strings(self):
        from app.core.config import settings

        for origin in settings.CORS_ORIGIN_LIST:
            assert isinstance(origin, str)
            assert origin.startswith("http")


class TestSecurityConfig:
    """Test security-related configuration defaults."""

    def test_token_expiry_is_reasonable(self):
        from app.core.config import settings

        # Should be at most 24 hours (1440 minutes)
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES <= 1440

    def test_algorithm_is_set(self):
        from app.core.config import settings

        assert settings.ALGORITHM == "HS256"


class TestRateLimitConfig:
    """Test rate limiting configuration."""

    def test_rate_limit_has_default(self):
        from app.core.config import settings

        assert settings.RATE_LIMIT_PER_MINUTE > 0

    def test_rate_limit_is_reasonable(self):
        from app.core.config import settings

        # Should be between 10 and 10000
        assert 10 <= settings.RATE_LIMIT_PER_MINUTE <= 10000
