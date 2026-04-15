"""Request logging middleware.

Logs every request with method, path, status code, and duration in a
structured format using *structlog*.  A correlation ID is extracted from
the ``X-Request-ID`` header (or generated) and bound to the log context
for the duration of the request.
"""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING

import structlog
from starlette.middleware.base import BaseHTTPMiddleware

from apic_vibe_portal_bff.utils.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

    from starlette.requests import Request
    from starlette.responses import Response

logger = get_logger(__name__)


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """Log every HTTP request with timing and correlation ID."""

    async def dispatch(self, request: Request, call_next: Callable[..., Response]) -> Response:
        """Process the request and log timing information."""
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start = time.perf_counter()
        status_code: int | None = None
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            status_code = 500
            raise
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                duration_ms=duration_ms,
                request_id=request_id,
            )

        response.headers["X-Request-ID"] = request_id
        return response
