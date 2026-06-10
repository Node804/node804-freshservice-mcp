"""Shared HTTP client, authentication, rate-limit handling, caching, and utilities."""

import asyncio
import base64
import functools
import logging
import os
import re
import time
from typing import Any, Dict, Optional, Tuple

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# --- Credential validation at import time ---
FRESHSERVICE_DOMAIN = os.getenv("FRESHSERVICE_DOMAIN")
FRESHSERVICE_APIKEY = os.getenv("FRESHSERVICE_APIKEY")

if not FRESHSERVICE_DOMAIN:
    raise RuntimeError(
        "FRESHSERVICE_DOMAIN environment variable is required. "
        "Set it to your Freshservice subdomain (e.g. yourcompany.freshservice.com)."
    )

if not FRESHSERVICE_APIKEY:
    raise RuntimeError(
        "FRESHSERVICE_APIKEY environment variable is required. "
        "Set it to your Freshservice API key."
    )

# --- Cache TTL (seconds) — configurable via env, default 1 hour ---
try:
    CACHE_TTL = int(os.getenv("FRESHSERVICE_CACHE_TTL", "3600"))
except ValueError:
    logger.warning("Invalid FRESHSERVICE_CACHE_TTL, falling back to 3600")
    CACHE_TTL = 3600


def get_auth_headers() -> Dict[str, str]:
    """Return HTTP headers with Basic auth for the Freshservice API."""
    token = base64.b64encode(f"{FRESHSERVICE_APIKEY}:X".encode()).decode()
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
    }


# --- Rate-limit state (updated by RateLimitTransport on every response) ---
rate_limit_remaining: Optional[int] = None
rate_limit_total: Optional[int] = None


class RateLimitTransport(httpx.AsyncBaseTransport):
    """Transport wrapper that handles Freshservice rate-limit headers and 429 retries.

    On every response:
      - Reads X-RateLimit-Remaining / X-RateLimit-Total and updates module-level state
      - On HTTP 429: reads Retry-After header, waits, and retries (up to max_retries)
    """

    def __init__(
        self,
        transport: httpx.AsyncBaseTransport,
        max_retries: int = 3,
    ) -> None:
        self._transport = transport
        self._max_retries = max_retries

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        global rate_limit_remaining, rate_limit_total

        for attempt in range(self._max_retries + 1):
            response = await self._transport.handle_async_request(request)

            # Track rate-limit headers on every response
            remaining = response.headers.get("x-ratelimit-remaining")
            total = response.headers.get("x-ratelimit-total")
            if remaining is not None:
                try:
                    rate_limit_remaining = int(remaining)
                except ValueError:
                    pass
            if total is not None:
                try:
                    rate_limit_total = int(total)
                except ValueError:
                    pass

            if remaining is not None:
                logger.debug(
                    "Rate limit: %s/%s remaining",
                    rate_limit_remaining,
                    rate_limit_total or "?",
                )

            # If not rate-limited, return immediately
            if response.status_code != 429:
                return response

            # Rate-limited — retry if we have attempts left
            if attempt == self._max_retries:
                logger.warning(
                    "Rate limited (429) after %d retries, returning error response",
                    self._max_retries,
                )
                return response

            retry_after = response.headers.get("retry-after", "60")
            try:
                wait_seconds = int(retry_after)
            except ValueError:
                wait_seconds = 60

            logger.warning(
                "Rate limited (429). Retrying in %ds (attempt %d/%d)",
                wait_seconds,
                attempt + 1,
                self._max_retries,
            )
            await asyncio.sleep(wait_seconds)

        return response  # should not reach here, but satisfy type checker


# --- Shared AsyncClient ---
_client: Optional[httpx.AsyncClient] = None


def get_client() -> httpx.AsyncClient:
    """Return a module-level shared AsyncClient, creating it on first call."""
    global _client
    if _client is None or _client.is_closed:
        transport = RateLimitTransport(httpx.AsyncHTTPTransport())
        _client = httpx.AsyncClient(
            transport=transport,
            base_url=f"https://{FRESHSERVICE_DOMAIN}",
            headers=get_auth_headers(),
            timeout=30.0,
        )
    return _client


def parse_link_header(link_header: str) -> Dict[str, Optional[int]]:
    """Parse the Link header to extract pagination information.

    Args:
        link_header: The Link header string from the response

    Returns:
        Dictionary containing next and prev page numbers
    """
    pagination: Dict[str, Optional[int]] = {"next": None, "prev": None}
    if not link_header:
        return pagination

    links = link_header.split(",")
    for link in links:
        match = re.search(r'<(.+?)>;\s*rel="(.+?)"', link)
        if match:
            url, rel = match.groups()
            page_match = re.search(r"page=(\d+)", url)
            if page_match:
                pagination[rel] = int(page_match.group(1))

    return pagination


# --- TTL Response Cache ---


class TTLCache:
    """Simple time-based cache backed by a dict. No external dependencies."""

    def __init__(self, default_ttl: float = 300.0) -> None:
        self._store: Dict[str, Tuple[Any, float]] = {}
        self._default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        """Return cached value if present and not expired, else None."""
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Store a value with a TTL (seconds). Defaults to the cache's default TTL."""
        expires_at = time.monotonic() + (ttl if ttl is not None else self._default_ttl)
        self._store[key] = (value, expires_at)

    def clear(self) -> None:
        """Remove all entries."""
        self._store.clear()


# Module-level cache instance (shared across all cached tools)
_response_cache = TTLCache(default_ttl=CACHE_TTL)


def cached_response(ttl_seconds: Optional[int] = None):
    """Decorator that caches successful async tool responses.

    Args:
        ttl_seconds: Cache lifetime in seconds.  Defaults to ``CACHE_TTL``
            (from the ``FRESHSERVICE_CACHE_TTL`` env var, default 3600).

    Cache key is derived from function name + positional and keyword arguments.
    Only responses that do NOT contain an ``"error"`` key are cached.

    Usage::

        @conditional_tool()
        @cached_response()
        async def get_ticket_fields() -> Dict[str, Any]:
            ...
    """
    effective_ttl = ttl_seconds if ttl_seconds is not None else CACHE_TTL

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{args!r}:{sorted(kwargs.items())!r}"
            cached = _response_cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache hit for %s", func.__name__)
                return cached

            result = await func(*args, **kwargs)

            # Only cache successful responses
            if isinstance(result, dict) and "error" not in result:
                _response_cache.set(cache_key, result, ttl=effective_ttl)

            return result

        return wrapper

    return decorator


async def multipart_request(
    method: str,
    url: str,
    files: list,
    data: Optional[Dict[str, Any]] = None,
) -> httpx.Response:
    """Make a multipart/form-data request (for file uploads).

    The shared client has Content-Type: application/json as a default header.
    This helper overrides headers per-request so httpx can set the correct
    multipart boundary automatically.

    Args:
        method: HTTP method (PUT, POST, etc.)
        url: API endpoint path (e.g. /api/v2/tickets/123)
        files: List of (field_name, (filename, file_bytes, content_type)) tuples
        data: Optional dict of additional form fields

    Returns:
        The httpx.Response object.
    """
    client = get_client()
    # The shared client has Content-Type: application/json which breaks
    # multipart uploads.  Create a one-off client that inherits only the
    # auth header and base URL so httpx can set the multipart boundary.
    auth_header = client.headers.get("authorization", "")
    async with httpx.AsyncClient(
        base_url=str(client.base_url),
        headers={"Authorization": auth_header},
        timeout=30.0,
    ) as mp_client:
        return await mp_client.request(method, url, files=files, data=data or {})


def clear_response_cache() -> int:
    """Clear all cached responses and return the number of entries removed."""
    count = len(_response_cache._store)
    _response_cache.clear()
    logger.info("Response cache cleared (%d entries)", count)
    return count
