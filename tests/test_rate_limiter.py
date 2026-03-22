"""Tests for the rate limiting middleware."""

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.middleware import RateLimitMiddleware


class TestRateLimitMiddleware:
    def _make_middleware(self, rpm: int = 5):
        app = MagicMock()
        mw = RateLimitMiddleware(app, requests_per_minute=rpm)
        return mw

    def test_cleanup_removes_old_timestamps(self):
        mw = self._make_middleware()
        now = time.time()
        timestamps = [now - 120, now - 90, now - 30, now - 10, now]
        result = mw._cleanup(timestamps, now)
        # Only the last 3 should remain (within 60s window)
        assert len(result) == 3

    def test_cleanup_keeps_recent_timestamps(self):
        mw = self._make_middleware()
        now = time.time()
        timestamps = [now - 5, now - 3, now - 1]
        result = mw._cleanup(timestamps, now)
        assert len(result) == 3

    def test_cleanup_empty_list(self):
        mw = self._make_middleware()
        assert mw._cleanup([], time.time()) == []

    def test_get_client_ip_from_direct_connection(self):
        mw = self._make_middleware()
        request = MagicMock()
        request.headers = {}
        request.client.host = "192.168.1.1"
        assert mw._get_client_ip(request) == "192.168.1.1"

    def test_get_client_ip_from_forwarded_header(self):
        mw = self._make_middleware()
        request = MagicMock()
        request.headers = {"x-forwarded-for": "10.0.0.1, 10.0.0.2"}
        assert mw._get_client_ip(request) == "10.0.0.1"

    @pytest.mark.asyncio
    async def test_exempt_paths_are_not_limited(self):
        mw = self._make_middleware(rpm=1)
        request = MagicMock()
        request.url.path = "/health"
        call_next = AsyncMock(return_value=MagicMock(status_code=200))

        # Should pass through even with rpm=1
        for _ in range(5):
            await mw.dispatch(request, call_next)
        assert call_next.call_count == 5

    @pytest.mark.asyncio
    async def test_rate_limit_blocks_excess_requests(self):
        mw = self._make_middleware(rpm=3)
        request = MagicMock()
        request.url.path = "/api/test"
        request.headers = {}
        request.client.host = "1.2.3.4"
        call_next = AsyncMock(return_value=MagicMock(status_code=200))

        responses = []
        for _ in range(5):
            resp = await mw.dispatch(request, call_next)
            responses.append(resp)

        # First 3 should pass, last 2 should be 429
        status_codes = [r.status_code for r in responses]
        assert status_codes[:3] == [200, 200, 200]
        assert status_codes[3] == 429
        assert status_codes[4] == 429
