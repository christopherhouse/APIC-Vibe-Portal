"""JWT authentication middleware for Entra ID (Azure AD).

Validates Bearer tokens from Entra ID using JWKS (JSON Web Key Sets).
Extracts user claims and attaches them to ``request.state.user``.
Health-check and OpenAPI documentation paths are exempt from authentication.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import jwt
from jwt import PyJWKClient
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from apic_vibe_portal_bff.config.settings import get_settings
from apic_vibe_portal_bff.utils.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

    from starlette.requests import Request
    from starlette.responses import Response

logger = get_logger(__name__)

# Paths that do not require authentication
_PUBLIC_PATHS: set[str] = {
    "/health",
    "/health/ready",
    "/docs",
    "/openapi.json",
    "/redoc",
}


@dataclass
class AuthenticatedUser:
    """Represents the authenticated user extracted from a JWT."""

    oid: str
    name: str
    email: str
    roles: list[str] = field(default_factory=list)
    claims: dict[str, Any] = field(default_factory=dict)


# Module-level cache for the JWKS client (one per process)
_jwks_client: PyJWKClient | None = None


def _get_jwks_client(tenant_id: str) -> PyJWKClient:
    """Return a cached ``PyJWKClient`` for the given tenant."""
    global _jwks_client  # noqa: PLW0603
    if _jwks_client is None:
        jwks_uri = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
        _jwks_client = PyJWKClient(jwks_uri, cache_keys=True)
    return _jwks_client


def reset_jwks_client() -> None:
    """Reset the cached JWKS client (used in tests)."""
    global _jwks_client  # noqa: PLW0603
    _jwks_client = None


def validate_token(token: str) -> AuthenticatedUser:
    """Validate an Entra ID JWT and return an ``AuthenticatedUser``.

    Raises ``jwt.InvalidTokenError`` (or subclasses) on failure.
    """
    settings = get_settings()
    tenant_id = settings.entra_tenant_id
    client_id = settings.entra_client_id
    audience = settings.entra_audience or client_id

    if not tenant_id or not client_id:
        raise jwt.InvalidTokenError("Entra ID is not configured on the server")

    jwks_client = _get_jwks_client(tenant_id)
    signing_key = jwks_client.get_signing_key_from_jwt(token)

    issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"

    decoded: dict[str, Any] = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=audience,
        issuer=issuer,
        options={
            "verify_exp": True,
            "verify_aud": True,
            "verify_iss": True,
        },
    )

    return AuthenticatedUser(
        oid=decoded.get("oid", ""),
        name=decoded.get("name", ""),
        email=decoded.get("preferred_username", decoded.get("email", "")),
        roles=decoded.get("roles", []),
        claims=decoded,
    )


class AuthMiddleware(BaseHTTPMiddleware):
    """Validate Entra ID Bearer tokens on incoming requests.

    Populates ``request.state.user`` with an ``AuthenticatedUser`` instance
    on success.  Returns 401 for missing/invalid tokens on protected paths.
    """

    async def dispatch(self, request: Request, call_next: Callable[..., Response]) -> Response:
        path = request.url.path

        # Allow public paths without auth
        if path in _PUBLIC_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid Authorization header"},
            )

        token = auth_header[len("Bearer ") :]
        try:
            user = validate_token(token)
        except jwt.ExpiredSignatureError:
            logger.warning("auth.token_expired")
            return JSONResponse(
                status_code=401,
                content={"detail": "Token has expired"},
            )
        except jwt.InvalidTokenError as exc:
            logger.warning("auth.invalid_token", error=str(exc))
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid token"},
            )

        request.state.user = user
        return await call_next(request)
