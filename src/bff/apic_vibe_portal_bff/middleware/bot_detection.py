"""Bot detection middleware for the BFF API.

Implements basic bot detection heuristics to identify and block automated
requests. Detection is based on:
- User-Agent analysis (missing, empty, or known bot signatures)
- Request pattern anomalies

Blocked requests receive a 403 Forbidden response.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

if TYPE_CHECKING:
    from collections.abc import Callable

    from starlette.requests import Request
    from starlette.responses import Response

# Known bot User-Agent patterns to block
# These are automated tools / scrapers, not legitimate search engine crawlers.
_BLOCKED_BOT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"python-requests",
        r"python-urllib",
        r"java/\d",
        r"libwww-perl",
        r"wget",
        r"curl/\d",
        r"scrapy",
        r"httpclient",
        r"go-http-client",
        r"php/\d",
        r"axios/\d",
        r"node-fetch",
        r"okhttp",
        r"httpie",
        r"rest-client",
        r"insomnia",
    ]
]

# Patterns that indicate legitimate browsers
_BROWSER_PATTERNS: list[re.Pattern[str]] = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"Mozilla/\d",
        r"Chrome/\d",
        r"Safari/\d",
        r"Firefox/\d",
        r"Edge/\d",
        r"Opera/\d",
    ]
]

# Paths that bypass bot detection (health checks, etc.)
_EXEMPT_PATHS: set[str] = {
    "/health",
    "/healthz",
    "/ready",
    "/readyz",
    "/metrics",
}


class BotDetectionMiddleware(BaseHTTPMiddleware):
    """Middleware to detect and block automated bot requests.

    Args:
        app: The ASGI application.
        block_missing_ua: Block requests with missing/empty User-Agent.
        block_known_bots: Block requests matching known bot patterns.
        exempt_paths: Additional paths to exempt from bot detection.
    """

    def __init__(
        self,
        app: object,
        block_missing_ua: bool = True,
        block_known_bots: bool = True,
        exempt_paths: set[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.block_missing_ua = block_missing_ua
        self.block_known_bots = block_known_bots
        self.exempt_paths = _EXEMPT_PATHS | (exempt_paths or set())

    def _is_blocked_bot(self, user_agent: str) -> bool:
        """Check if the User-Agent matches a known blocked bot pattern."""
        return any(pattern.search(user_agent) for pattern in _BLOCKED_BOT_PATTERNS)

    def _is_browser(self, user_agent: str) -> bool:
        """Check if the User-Agent appears to be a legitimate browser."""
        return any(pattern.search(user_agent) for pattern in _BROWSER_PATTERNS)

    def _is_exempt(self, path: str) -> bool:
        """Check if the request path is exempt from bot detection."""
        return path.rstrip("/") in self.exempt_paths or path in self.exempt_paths

    async def dispatch(self, request: Request, call_next: Callable[..., Response]) -> Response:
        """Process the request through bot detection checks."""
        # Skip bot detection for exempt paths
        if self._is_exempt(request.url.path):
            return await call_next(request)

        user_agent = request.headers.get("user-agent", "").strip()

        # Block missing User-Agent
        if self.block_missing_ua and not user_agent:
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Forbidden",
                    "detail": "Request blocked: missing User-Agent header.",
                },
            )

        # Block known bot signatures
        if self.block_known_bots and user_agent and self._is_blocked_bot(user_agent):
            # Allow if it also looks like a browser (some legitimate tools include bot strings)
            if not self._is_browser(user_agent):
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "Forbidden",
                        "detail": "Request blocked: automated client detected.",
                    },
                )

        return await call_next(request)
