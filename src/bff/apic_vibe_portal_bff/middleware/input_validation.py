"""Input validation and sanitization middleware for the BFF API.

Provides request-level validation:
- Content-Type enforcement for POST/PUT/PATCH requests
- Request body size limits
- JSON body validation
- Path traversal detection
- HTML/script tag sanitization for string values
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from urllib.parse import unquote_plus

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

if TYPE_CHECKING:
    from collections.abc import Callable

    from starlette.requests import Request
    from starlette.responses import Response


# Maximum request body size (1 MB default)
DEFAULT_MAX_BODY_SIZE = 1_048_576

# Methods that carry a request body
_BODY_METHODS = {"POST", "PUT", "PATCH"}

# Dangerous patterns in path or query parameters
_PATH_TRAVERSAL_PATTERN = re.compile(r"\.\./|\.\.\\|%2e%2e%2f|%2e%2e/|\.\.%2f", re.IGNORECASE)

# HTML/script injection patterns
_SCRIPT_INJECTION_PATTERN = re.compile(
    r"<\s*script[^>]*>|<\s*/\s*script\s*>|javascript\s*:|on\w+\s*=",
    re.IGNORECASE,
)

# SQL injection patterns (basic detection)
_SQL_INJECTION_PATTERN = re.compile(
    r"(\b(UNION|SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|EXEC|EXECUTE)\b\s+"
    r"|(--|#|/\*)\s*$"
    r"|'\s*(OR|AND)\s+')",
    re.IGNORECASE,
)

# Paths exempt from validation (health checks, etc.)
_EXEMPT_PATHS: set[str] = {
    "/health",
    "/healthz",
    "/ready",
    "/readyz",
    "/metrics",
}


def sanitize_string(value: str) -> str:
    """Remove potentially dangerous HTML/script content from a string.

    Args:
        value: The input string to sanitize.

    Returns:
        The sanitized string with script tags and event handlers removed.
    """
    # Remove script tags and their content
    sanitized = re.sub(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", "", value, flags=re.IGNORECASE | re.DOTALL)
    # Remove remaining HTML tags
    sanitized = re.sub(r"<[^>]+>", "", sanitized)
    return sanitized


class InputValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for validating and sanitizing incoming requests.

    Args:
        app: The ASGI application.
        max_body_size: Maximum allowed request body size in bytes.
        check_content_type: Enforce Content-Type for body-carrying methods.
        check_path_traversal: Detect path traversal attempts.
        check_injection: Detect common injection patterns.
        exempt_paths: Additional paths to exempt from validation.
    """

    def __init__(
        self,
        app: object,
        max_body_size: int = DEFAULT_MAX_BODY_SIZE,
        check_content_type: bool = True,
        check_path_traversal: bool = True,
        check_injection: bool = True,
        exempt_paths: set[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.max_body_size = max_body_size
        self.check_content_type = check_content_type
        self.check_path_traversal = check_path_traversal
        self.check_injection = check_injection
        self.exempt_paths = _EXEMPT_PATHS | (exempt_paths or set())

    def _is_exempt(self, path: str) -> bool:
        """Check if the request path is exempt from validation."""
        return path.rstrip("/") in self.exempt_paths or path in self.exempt_paths

    def _check_path(self, path: str, query: str) -> str | None:
        """Check path and query string for traversal and injection patterns.

        Returns an error message if a violation is found, None otherwise.
        """
        full_path = f"{path}?{query}" if query else path
        # Decode URL-encoded characters for pattern matching
        decoded = unquote_plus(full_path)

        if self.check_path_traversal and _PATH_TRAVERSAL_PATTERN.search(decoded):
            return "Path traversal detected."

        if self.check_injection:
            if _SCRIPT_INJECTION_PATTERN.search(decoded):
                return "Potential script injection detected in URL."
            if _SQL_INJECTION_PATTERN.search(decoded):
                return "Potential SQL injection detected in URL."

        return None

    async def dispatch(self, request: Request, call_next: Callable[..., Response]) -> Response:
        """Process the request through input validation checks."""
        # Skip validation for exempt paths
        if self._is_exempt(request.url.path):
            return await call_next(request)

        # Check path and query string
        path_error = self._check_path(request.url.path, str(request.query_params))
        if path_error:
            return JSONResponse(
                status_code=400,
                content={"error": "Bad Request", "detail": path_error},
            )

        # Validate Content-Type for body-carrying requests
        if self.check_content_type and request.method in _BODY_METHODS:
            content_type = request.headers.get("content-type", "")
            if not content_type:
                return JSONResponse(
                    status_code=415,
                    content={
                        "error": "Unsupported Media Type",
                        "detail": "Content-Type header is required for request body.",
                    },
                )
            # Accept JSON and form data
            allowed_types = ("application/json", "multipart/form-data", "application/x-www-form-urlencoded")
            if not any(content_type.startswith(t) for t in allowed_types):
                return JSONResponse(
                    status_code=415,
                    content={
                        "error": "Unsupported Media Type",
                        "detail": f"Content-Type '{content_type}' is not supported.",
                    },
                )

        # Check body size for body-carrying requests
        if request.method in _BODY_METHODS:
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.max_body_size:
                return JSONResponse(
                    status_code=413,
                    content={
                        "error": "Payload Too Large",
                        "detail": f"Request body exceeds maximum size of {self.max_body_size} bytes.",
                    },
                )

        return await call_next(request)
