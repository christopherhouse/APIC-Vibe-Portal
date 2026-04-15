"""Global error handler middleware.

Catches unhandled exceptions and returns a consistent JSON error response.
In production mode, stack traces are suppressed from the response body.
"""

from __future__ import annotations

import traceback
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from apic_vibe_portal_bff.utils.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

    from starlette.requests import Request
    from starlette.responses import Response

logger = get_logger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Catch-all middleware that returns structured JSON error responses.

    Args:
        app: The ASGI application.
        debug: When ``True`` the traceback is included in the response.
    """

    def __init__(self, app: object, debug: bool = False) -> None:
        super().__init__(app)
        self.debug = debug

    async def dispatch(self, request: Request, call_next: Callable[..., Response]) -> Response:
        """Wrap the downstream handler and catch unhandled exceptions."""
        try:
            return await call_next(request)
        except Exception as exc:
            logger.error(
                "unhandled_exception",
                path=request.url.path,
                method=request.method,
                error=str(exc),
                exc_info=True,
            )

            request_id = request.headers.get("x-request-id")
            detail: str | dict[str, str] = "An unexpected error occurred."
            if self.debug:
                detail = {
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                }

            content: dict[str, str | dict[str, str]] = {
                "error": "Internal Server Error",
                "detail": detail,
            }
            if request_id:
                content["request_id"] = request_id

            response = JSONResponse(
                status_code=500,
                content=content,
            )
            if request_id:
                response.headers["X-Request-ID"] = request_id
            return response
