"""Domain exceptions for the API Center data-plane client.

These exceptions are shared between the BFF and indexer so that both
consumers handle errors consistently.
"""

from __future__ import annotations


class ApiCenterClientError(Exception):
    """Base error raised by the API Center data-plane client."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ApiCenterNotFoundError(ApiCenterClientError):
    """Raised when the requested resource does not exist (HTTP 404)."""

    def __init__(self, resource: str) -> None:
        super().__init__(f"Resource not found: {resource}", status_code=404)


class ApiCenterAuthError(ApiCenterClientError):
    """Raised when authentication / authorization fails (HTTP 401/403)."""

    def __init__(self, detail: str = "Unauthorized") -> None:
        super().__init__(detail, status_code=401)


class ApiCenterUnavailableError(ApiCenterClientError):
    """Raised when the API Center service is unavailable (HTTP 5xx)."""

    def __init__(self, detail: str = "Service unavailable") -> None:
        super().__init__(detail, status_code=503)
