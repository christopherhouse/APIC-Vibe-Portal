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

        response = await call_next(request)

        # Set http.route and X-Trace-ID after routing so we can use the matched
        # route template (e.g. ``/api/catalog/{api_id}``) instead of the concrete
        # request path.  Using the template prevents per-request cardinality
        # explosion in distributed traces and dashboards.
        if span.is_recording():
            matched_route = request.scope.get("route")
            route = getattr(matched_route, "path", request.url.path)
            span.set_attribute("http.route", route)

            # Write trace_id to response header only when the span context is valid
            # (non-zero).  Returning an all-zero trace-id misleads clients.
            ctx = span.get_span_context()
            if ctx and ctx.is_valid:
                trace_id_hex = format(ctx.trace_id, "032x")
                response.headers["X-Trace-ID"] = trace_id_hex

        return response
