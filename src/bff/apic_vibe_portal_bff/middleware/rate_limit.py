"""Rate limiting middleware for the BFF API.

Implements per-user and per-IP rate limiting using an in-memory sliding window
counter. Returns 429 Too Many Requests with Retry-After header when limits are
exceeded.

Defaults:
    - 100 requests/minute per authenticated user
    - 1000 requests/minute per IP address
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

if TYPE_CHECKING:
    from collections.abc import Callable

    from starlette.requests import Request
    from starlette.responses import Response


@dataclass
class _TokenBucket:
    """Simple token bucket for rate limiting."""

    capacity: float
    refill_rate: float  # tokens per second
    tokens: float = field(init=False)
    last_refill: float = field(init=False)

    def __post_init__(self) -> None:
        self.tokens = self.capacity
        self.last_refill = time.monotonic()

    def consume(self) -> bool:
        """Try to consume one token. Returns True if allowed, False if rate limited."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

    def retry_after(self) -> int:
        """Seconds until a token becomes available."""
        if self.tokens >= 1.0:
            return 0
        deficit = 1.0 - self.tokens
        return max(1, int(deficit / self.refill_rate) + 1)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using token bucket algorithm.

    Applies two layers of rate limiting:
    1. Per-user limit (based on authenticated user identity from token)
    2. Per-IP limit (based on client IP address)

    Args:
        app: The ASGI application.
        user_requests_per_minute: Max requests per minute per authenticated user.
        ip_requests_per_minute: Max requests per minute per IP address.
    """

    def __init__(
        self,
        app: object,
        user_requests_per_minute: int = 100,
        ip_requests_per_minute: int = 1000,
    ) -> None:
        super().__init__(app)
        self.user_requests_per_minute = user_requests_per_minute
        self.ip_requests_per_minute = ip_requests_per_minute
        self._user_buckets: dict[str, _TokenBucket] = defaultdict(
            lambda: _TokenBucket(
                capacity=float(user_requests_per_minute),
                refill_rate=user_requests_per_minute / 60.0,
            )
        )
        self._ip_buckets: dict[str, _TokenBucket] = defaultdict(
            lambda: _TokenBucket(
                capacity=float(ip_requests_per_minute),
                refill_rate=ip_requests_per_minute / 60.0,
            )
        )

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request, checking X-Forwarded-For header."""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP (original client) from the chain
            return forwarded_for.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    def _get_user_id(self, request: Request) -> str | None:
        """Extract user identifier from request state (set by auth middleware)."""
        return getattr(request.state, "user_id", None) if hasattr(request, "state") else None

    async def dispatch(self, request: Request, call_next: Callable[..., Response]) -> Response:
        """Process the request through rate limiting checks."""
        client_ip = self._get_client_ip(request)

        # Check IP-based rate limit
        ip_bucket = self._ip_buckets[client_ip]
        if not ip_bucket.consume():
            retry_after = ip_bucket.retry_after()
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "detail": "IP rate limit exceeded.",
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        # Check user-based rate limit (if authenticated)
        user_id = self._get_user_id(request)
        if user_id:
            user_bucket = self._user_buckets[user_id]
            if not user_bucket.consume():
                retry_after = user_bucket.retry_after()
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Too Many Requests",
                        "detail": "User rate limit exceeded.",
                        "retry_after": retry_after,
                    },
                    headers={"Retry-After": str(retry_after)},
                )

        response = await call_next(request)
        return response
