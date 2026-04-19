"""OTel-aware request middleware.

Enriches the active OTel span with custom attributes for every HTTP request:
``http.request_id``, ``http.route``, and basic user info when available.
This supplements the automatic FastAPI instrumentation provided by the
Azure Monitor OTel distro.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from opentelemetry import trace
from starlette.middleware.base import BaseHTTPMiddleware

if TYPE_CHECKING:
    from collections.abc import Callable

    from starlette.requests import Request
    from starlette.responses import Response


class OTelEnrichmentMiddleware(BaseHTTPMiddleware):
    """Enrich the active OTel span with request-level attributes."""

    async def dispatch(self, request: Request, call_next: Callable[..., Response]) -> Response:
        """Add custom span attributes to the current span."""
        span = trace.get_current_span()
        if span.is_recording():
            request_id = request.headers.get("x-request-id", "")
            if request_id:
                span.set_attribute("http.request_id", request_id)
            # route pattern is only available after routing; best-effort
            route = getattr(request, "scope", {}).get("path", request.url.path)
            span.set_attribute("http.route", route)

        response = await call_next(request)

        # Write trace_id to response header for client-side correlation
        if span.is_recording():
            ctx = span.get_span_context()
            if ctx and ctx.trace_id:
                trace_id_hex = format(ctx.trace_id, "032x")
                response.headers["X-Trace-ID"] = trace_id_hex

        return response
