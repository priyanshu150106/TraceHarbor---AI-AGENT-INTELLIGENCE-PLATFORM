"""
TraceHarbor API — Bounded In-Memory Rate Limiter & Abuse Prevention

Implements sliding-window rate limiting with strict memory bounds (LRU eviction).
Protects the API and public portfolio demo from query flooding, scraping, and DoS.
"""

import ipaddress
import time
from collections import OrderedDict

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings

EXEMPT_PREFIXES = (
    "/health",
    "/healthz",
    "/readyz",
    "/docs",
    "/redoc",
    "/openapi.json",
)


class BoundedSlidingWindowLimiter:
    """
    Sliding-window rate limiter backed by a bounded OrderedDict.
    Enforces a strict upper bound on tracked keys to prevent memory exhaustion in multi-user deployments.
    """

    def __init__(self, max_keys: int = 10000):
        self.max_keys = max_keys
        self._store: OrderedDict[str, list[float]] = OrderedDict()

    def check(
        self, key: str, max_requests: int, window_seconds: int = 60
    ) -> tuple[bool, int, int]:
        """
        Check whether the request is allowed under the rate limit.
        Returns:
            allowed (bool): True if under limit, False if exceeded.
            remaining (int): Remaining requests allowed in window.
            reset_seconds (int): Seconds until window resets.
        """
        now = time.monotonic()
        cutoff = now - window_seconds

        # Retrieve or initialize timestamp list
        if key in self._store:
            self._store.move_to_end(key)
            timestamps = self._store[key]
        else:
            if len(self._store) >= self.max_keys:
                # Evict oldest tracked key to maintain bounded memory
                self._store.popitem(last=False)
            timestamps = []
            self._store[key] = timestamps

        # Prune timestamps outside window
        valid_timestamps = [t for t in timestamps if t > cutoff]
        self._store[key] = valid_timestamps

        count = len(valid_timestamps)
        if count >= max_requests:
            oldest = valid_timestamps[0]
            reset_seconds = max(1, int(window_seconds - (now - oldest)))
            return False, 0, reset_seconds

        # Record this request
        valid_timestamps.append(now)
        remaining = max_requests - len(valid_timestamps)
        reset_seconds = window_seconds
        return True, remaining, reset_seconds

    def reset(self) -> None:
        """Clear all rate limit state (useful in testing)."""
        self._store.clear()


# Global limiter instance
rate_limiter = BoundedSlidingWindowLimiter(max_keys=10000)


def is_valid_ip(ip_str: str) -> bool:
    """Validate whether an IP address string is valid IPv4 or IPv6."""
    try:
        ipaddress.ip_address(ip_str.strip())
        return True
    except (ValueError, AttributeError):
        return False


def get_client_ip(request: Request) -> str:
    """
    Extract client IP securely handling reverse proxy environments.

    Protects against IP spoofing:
    - Never trusts X-Forwarded-For from untrusted direct peers unless proxy_headers_enabled is True
      or peer IP is in trusted_proxies.
    - When behind a trusted proxy, resolves the rightmost valid client IP to prevent
      client-injected spoofed headers from bypassing rate limits.
    - Validates that IP strings conform to valid IPv4/IPv6 syntax.
    - Falls back to request.client.host (or 127.0.0.1) if headers are missing, untrusted, or invalid.
    """
    peer_ip = request.client.host if request.client else "127.0.0.1"

    # Only trust proxy headers if explicitly enabled or peer is in trusted_proxies
    is_trusted_peer = (
        settings.proxy_headers_enabled
        or peer_ip in settings.trusted_proxies
        or "*" in settings.trusted_proxies
    )

    if not is_trusted_peer:
        return peer_ip

    # Cloudflare / Render edge provides CF-Connecting-IP, sanitized and overwritten at edge
    cf_connecting_ip = request.headers.get("CF-Connecting-IP")
    if cf_connecting_ip:
        candidate = cf_connecting_ip.strip()
        if is_valid_ip(candidate):
            return candidate

    # Vercel Edge specifically injects X-Vercel-Forwarded-For or overwrites X-Forwarded-For
    vercel_forwarded_for = request.headers.get("X-Vercel-Forwarded-For")
    if vercel_forwarded_for:
        candidate = vercel_forwarded_for.split(",")[0].strip()
        if is_valid_ip(candidate):
            return candidate

    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Split hops: e.g. "spoofed_client_ip, real_client_ip, proxy_ip"
        hops = [h.strip() for h in forwarded_for.split(",") if h.strip()]
        # Traverse right-to-left: the trusted reverse proxy appends the connecting client IP
        for candidate in reversed(hops):
            if is_valid_ip(candidate) and (candidate not in settings.trusted_proxies or len(hops) == 1):
                return candidate
        # If all valid candidates were trusted proxies, return the rightmost valid one
        for candidate in reversed(hops):
            if is_valid_ip(candidate):
                return candidate

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        candidate = real_ip.strip()
        if is_valid_ip(candidate):
            return candidate

    return peer_ip


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware applying tiered rate limits:
    - Public/Demo Visitors: settings.rate_limit_demo_per_minute
    - Authenticated API Keys: settings.rate_limit_auth_per_minute
    - Exempt: Health probes and OpenAPI documentation
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if not settings.rate_limit_enabled:
            return await call_next(request)

        path = request.url.path
        if any(path == p or path.startswith(p + "/") for p in EXEMPT_PREFIXES):
            return await call_next(request)

        # Determine rate limit key and allowance
        raw_key = (
            request.headers.get("X-API-Key")
            or request.headers.get("Authorization")
        )
        if raw_key and raw_key.strip():
            # Authenticated caller
            import hashlib

            key_hash = hashlib.sha256(raw_key.strip().encode("utf-8")).hexdigest()[:16]
            rate_key = f"key:{key_hash}"
            limit = settings.rate_limit_auth_per_minute
        else:
            # Public demo / unauthenticated caller
            client_ip = get_client_ip(request)
            rate_key = f"ip:{client_ip}"
            limit = settings.rate_limit_demo_per_minute

        allowed, remaining, reset_sec = rate_limiter.check(
            rate_key, max_requests=limit, window_seconds=60
        )

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": (
                        f"Rate limit exceeded. Maximum {limit} requests per minute. "
                        f"Please retry after {reset_sec} seconds."
                    )
                },
                headers={
                    "Retry-After": str(reset_sec),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_sec),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_sec)
        return response

