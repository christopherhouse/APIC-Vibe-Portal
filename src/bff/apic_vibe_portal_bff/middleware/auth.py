"""JWT authentication middleware for Entra ID (Azure AD).

Validates Bearer tokens from the Authorization header using JWKS (JSON Web Key Set)
fetched from the Entra ID OpenID Connect discovery endpoint. Extracts user claims
and attaches them to ``request.state.user`` for downstream use.

Health and OpenAPI endpoints are exempt from authentication.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import cachetools
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
EXEMPT_PATHS: set[str] = {
    "/health",
    "/health/ready",
    "/docs",
    "/redoc",
    "/openapi.json",
}

# Cache for JWKS client (keyed by tenant ID, TTL 24 hours)
_jwks_client_cache: cachetools.TTLCache[str, PyJWKClient] = cachetools.TTLCache(maxsize=4, ttl=86400)


@dataclass
class AuthenticatedUser:
    """Represents an authenticated user extracted from JWT claims."""

    oid: str
    name: str = ""
    email: str = ""
    roles: list[str] = field(default_factory=list)
    raw_claims: dict = field(default_factory=dict)


def _get_jwks_client(tenant_id: str) -> PyJWKClient:
    """Return a cached PyJWKClient for the given tenant."""
    if tenant_id not in _jwks_client_cache:
        jwks_uri = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
        _jwks_client_cache[tenant_id] = PyJWKClient(jwks_uri, cache_keys=True)
    return _jwks_client_cache[tenant_id]


def validate_token(token: str, tenant_id: str, client_id: str, audience: str) -> AuthenticatedUser:
    """Validate a JWT token from Entra ID and return an AuthenticatedUser.

    Parameters
    ----------
    token:
        The raw JWT bearer token string.
    tenant_id:
        The Entra ID tenant ID.
    client_id:
        The BFF application/client ID.
    audience:
        The expected audience claim.

    Returns
    -------
    AuthenticatedUser
        The authenticated user with claims extracted from the token.

    Raises
    ------
    jwt.InvalidTokenError
        If the token is invalid, expired, has wrong audience, etc.
    """
    jwks_client = _get_jwks_client(tenant_id)
    signing_key = jwks_client.get_signing_key_from_jwt(token)

    issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"

    payload = jwt.decode(
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
        oid=payload.get("oid", ""),
        name=payload.get("name", ""),
        email=payload.get("preferred_username", payload.get("email", "")),
        roles=payload.get("roles", []),
        raw_claims=payload,
    )


class AuthMiddleware(BaseHTTPMiddleware):
    """Validate Entra ID Bearer tokens and set ``request.state.user``.

    Exempt paths (health checks, OpenAPI docs) are passed through
    without authentication. All other requests must include a valid
    ``Authorization: Bearer <token>`` header.

    When ``entra_tenant_id`` is not configured (empty string), the
    middleware passes all requests through — this allows local development
    without Entra ID.
    """

    async def dispatch(self, request: Request, call_next: Callable[..., Response]) -> Response:
        """Validate the bearer token and attach user context."""
        # Allow exempt paths through without auth
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        settings = get_settings()

        # If Entra ID is not configured, pass through (local dev mode)
        if not settings.entra_tenant_id:
            return await call_next(request)

        # Extract Bearer token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized", "detail": "Missing or invalid Authorization header"},
            )

        token = auth_header[7:]  # Strip "Bearer " prefix

        try:
            user = validate_token(
                token=token,
                tenant_id=settings.entra_tenant_id,
                client_id=settings.entra_client_id,
                audience=settings.entra_audience,
            )
        except jwt.ExpiredSignatureError:
            logger.warning("auth.token_expired")
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized", "detail": "Token has expired"},
            )
        except jwt.InvalidAudienceError:
            logger.warning("auth.invalid_audience")
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized", "detail": "Invalid token audience"},
            )
        except jwt.InvalidIssuerError:
            logger.warning("auth.invalid_issuer")
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized", "detail": "Invalid token issuer"},
            )
        except jwt.InvalidTokenError as exc:
            logger.warning("auth.invalid_token", error=str(exc))
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized", "detail": "Invalid token"},
            )
        except Exception as exc:
            logger.error("auth.unexpected_error", error=str(exc))
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized", "detail": "Authentication failed"},
            )

        # Attach user to request state
        request.state.user = user
        return await call_next(request)
