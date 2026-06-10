"""Tests for client utilities: TTLCache, cached_response, and RateLimitTransport."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest


# ---------------------------------------------------------------------------
# TTLCache
# ---------------------------------------------------------------------------


def _import_cache():
    """Import cache class fresh (must happen after env vars are set by fixture)."""
    from node804_freshservice_mcp.client import TTLCache
    return TTLCache


class TestTTLCache:
    def test_set_and_get(self, mock_env):
        TTLCache = _import_cache()
        cache = TTLCache(default_ttl=60)
        cache.set("key1", {"data": 42})
        assert cache.get("key1") == {"data": 42}

    def test_cache_miss(self, mock_env):
        TTLCache = _import_cache()
        cache = TTLCache(default_ttl=60)
        assert cache.get("nonexistent") is None

    def test_expiry(self, mock_env, monkeypatch):
        TTLCache = _import_cache()
        cache = TTLCache(default_ttl=1)

        # Manually set an entry that expired 10 seconds ago
        cache._store["expired_key"] = ({"old": True}, time.monotonic() - 10)

        assert cache.get("expired_key") is None
        # Entry should have been evicted
        assert "expired_key" not in cache._store

    def test_custom_ttl_per_entry(self, mock_env):
        TTLCache = _import_cache()
        cache = TTLCache(default_ttl=300)
        cache.set("short", "value", ttl=0.001)
        time.sleep(0.01)
        assert cache.get("short") is None

    def test_clear(self, mock_env):
        TTLCache = _import_cache()
        cache = TTLCache(default_ttl=60)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_overwrite(self, mock_env):
        TTLCache = _import_cache()
        cache = TTLCache(default_ttl=60)
        cache.set("key", "first")
        cache.set("key", "second")
        assert cache.get("key") == "second"


# ---------------------------------------------------------------------------
# cached_response decorator
# ---------------------------------------------------------------------------


class TestCachedResponse:
    @pytest.mark.asyncio
    async def test_caches_successful_response(self, mock_env):
        from node804_freshservice_mcp.client import cached_response, _response_cache

        _response_cache.clear()
        call_count = 0

        @cached_response(ttl_seconds=60)
        async def my_tool():
            nonlocal call_count
            call_count += 1
            return {"fields": ["a", "b"]}

        result1 = await my_tool()
        result2 = await my_tool()

        assert result1 == {"fields": ["a", "b"]}
        assert result2 == {"fields": ["a", "b"]}
        assert call_count == 1  # second call was served from cache

    @pytest.mark.asyncio
    async def test_does_not_cache_error_response(self, mock_env):
        from node804_freshservice_mcp.client import cached_response, _response_cache

        _response_cache.clear()
        call_count = 0

        @cached_response(ttl_seconds=60)
        async def failing_tool():
            nonlocal call_count
            call_count += 1
            return {"error": "Failed to fetch"}

        result1 = await failing_tool()
        result2 = await failing_tool()

        assert "error" in result1
        assert call_count == 2  # both calls hit the function

    @pytest.mark.asyncio
    async def test_cache_key_includes_args(self, mock_env):
        from node804_freshservice_mcp.client import cached_response, _response_cache

        _response_cache.clear()
        call_count = 0

        @cached_response(ttl_seconds=60)
        async def get_by_id(item_id: int):
            nonlocal call_count
            call_count += 1
            return {"id": item_id}

        await get_by_id(1)
        await get_by_id(2)
        await get_by_id(1)  # should be cached

        assert call_count == 2  # id=1 cached, id=2 new, id=1 from cache


# ---------------------------------------------------------------------------
# RateLimitTransport
# ---------------------------------------------------------------------------


def _make_response(status_code: int, headers: dict = None) -> httpx.Response:
    """Create a minimal httpx.Response for testing."""
    return httpx.Response(
        status_code=status_code,
        headers=headers or {},
        content=b"{}",
        request=httpx.Request("GET", "https://test.freshservice.com/api/v2/test"),
    )


class TestRateLimitTransport:
    @pytest.mark.asyncio
    async def test_passes_through_normal_response(self, mock_env):
        from node804_freshservice_mcp.client import RateLimitTransport
        import node804_freshservice_mcp.client as client_mod

        inner = AsyncMock()
        inner.handle_async_request.return_value = _make_response(
            200, {"x-ratelimit-remaining": "450", "x-ratelimit-total": "500"}
        )

        transport = RateLimitTransport(inner, max_retries=3)
        request = httpx.Request("GET", "https://test.freshservice.com/api/v2/test")
        response = await transport.handle_async_request(request)

        assert response.status_code == 200
        assert client_mod.rate_limit_remaining == 450
        assert client_mod.rate_limit_total == 500
        assert inner.handle_async_request.call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_429(self, mock_env):
        from node804_freshservice_mcp.client import RateLimitTransport

        inner = AsyncMock()
        # First call returns 429, second returns 200
        inner.handle_async_request.side_effect = [
            _make_response(429, {"retry-after": "0"}),
            _make_response(200, {"x-ratelimit-remaining": "100"}),
        ]

        transport = RateLimitTransport(inner, max_retries=3)
        request = httpx.Request("GET", "https://test.freshservice.com/api/v2/test")
        response = await transport.handle_async_request(request)

        assert response.status_code == 200
        assert inner.handle_async_request.call_count == 2

    @pytest.mark.asyncio
    async def test_exhausts_retries(self, mock_env):
        from node804_freshservice_mcp.client import RateLimitTransport

        inner = AsyncMock()
        # All calls return 429
        inner.handle_async_request.return_value = _make_response(
            429, {"retry-after": "0"}
        )

        transport = RateLimitTransport(inner, max_retries=2)
        request = httpx.Request("GET", "https://test.freshservice.com/api/v2/test")
        response = await transport.handle_async_request(request)

        assert response.status_code == 429
        # 1 initial + 2 retries = 3 total calls
        assert inner.handle_async_request.call_count == 3

    @pytest.mark.asyncio
    async def test_updates_rate_limit_on_every_response(self, mock_env):
        from node804_freshservice_mcp.client import RateLimitTransport
        import node804_freshservice_mcp.client as client_mod

        inner = AsyncMock()
        inner.handle_async_request.return_value = _make_response(
            200, {"x-ratelimit-remaining": "42", "x-ratelimit-total": "1000"}
        )

        transport = RateLimitTransport(inner)
        request = httpx.Request("GET", "https://test.freshservice.com/api/v2/test")
        await transport.handle_async_request(request)

        assert client_mod.rate_limit_remaining == 42
        assert client_mod.rate_limit_total == 1000
