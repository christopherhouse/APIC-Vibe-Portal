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
    tenant_id = settings.bff_entra_tenant_id
    client_id = settings.bff_entra_client_id
    audience = settings.bff_entra_audience or client_id

    logger.info(
        "auth.validate_token.config",
        tenant_id=tenant_id[:8] + "..." if tenant_id else "<empty>",
        client_id=client_id[:8] + "..." if client_id else "<empty>",
        expected_audience=audience[:8] + "..." if audience else "<empty>",
    )

    if not tenant_id or not client_id:
        logger.error("auth.validate_token.missing_config", tenant_id_set=bool(tenant_id), client_id_set=bool(client_id))
        raise jwt.InvalidTokenError("Entra ID is not configured on the server")

    # Decode the token header without verification to log metadata
    unverified_claims: dict[str, Any] = {}
    try:
        unverified_header = jwt.get_unverified_header(token)
        unverified_claims = jwt.decode(token, options={"verify_signature": False})
        logger.info(
            "auth.validate_token.token_header",
            alg=unverified_header.get("alg"),
            kid=unverified_header.get("kid"),
            typ=unverified_header.get("typ"),
        )
        logger.info(
            "auth.validate_token.token_claims",
            token_issuer=unverified_claims.get("iss"),
            token_audience=unverified_claims.get("aud"),
            token_exp=unverified_claims.get("exp"),
            token_nbf=unverified_claims.get("nbf"),
            token_iat=unverified_claims.get("iat"),
            token_oid=unverified_claims.get("oid"),
            token_name=unverified_claims.get("name"),
            token_roles=unverified_claims.get("roles"),
            token_scp=unverified_claims.get("scp"),
            token_azp=unverified_claims.get("azp"),
            token_ver=unverified_claims.get("ver"),
        )
    except Exception:
        logger.warning(
            "auth.validate_token.unreadable_token",
            detail="Could not decode token header/claims for logging",
        )

    jwks_client = _get_jwks_client(tenant_id)

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
    except Exception as exc:
        logger.error(
            "auth.validate_token.jwks_failure",
            error=str(exc),
            jwks_uri=f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys",
        )
        raise

    issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"
    logger.info(
        "auth.validate_token.expected_values",
        expected_issuer=issuer,
        expected_audience=audience,
    )

    try:
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
    except jwt.ExpiredSignatureError:
        logger.warning("auth.validate_token.expired", token_exp=unverified_claims.get("exp"))
        raise
    except jwt.InvalidAudienceError:
        token_aud = unverified_claims.get("aud")
        logger.warning("auth.validate_token.audience_mismatch", expected_audience=audience, token_audience=token_aud)
        raise
    except jwt.InvalidIssuerError:
        token_iss = unverified_claims.get("iss")
        logger.warning("auth.validate_token.issuer_mismatch", expected_issuer=issuer, token_issuer=token_iss)
        raise
    except jwt.InvalidTokenError as exc:
        logger.warning("auth.validate_token.decode_failed", error=str(exc), error_type=type(exc).__name__)
        raise

    user = AuthenticatedUser(
        oid=decoded.get("oid", ""),
        name=decoded.get("name", ""),
        email=decoded.get("preferred_username", decoded.get("email", "")),
        roles=decoded.get("roles", []),
        claims=decoded,
    )

    logger.info(
        "auth.validate_token.success",
        user_oid=user.oid,
        user_name=user.name,
        user_roles=user.roles,
    )
    return user


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

        logger.info("auth.dispatch.checking", path=path, method=request.method)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            logger.warning(
                "auth.dispatch.missing_bearer",
                path=path,
                auth_header_present=bool(auth_header),
                auth_header_prefix=auth_header[:10] + "..." if auth_header else "<empty>",
            )
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid Authorization header"},
            )

        token = auth_header[len("Bearer ") :]
        logger.info(
            "auth.dispatch.token_received",
            path=path,
            token_length=len(token),
            token_prefix=token[:20] + "..." if len(token) > 20 else token,
        )
        try:
            user = validate_token(token)
        except jwt.ExpiredSignatureError:
            logger.warning("auth.dispatch.token_expired", path=path)
            return JSONResponse(
                status_code=401,
                content={"detail": "Token has expired"},
            )
        except jwt.InvalidTokenError as exc:
            logger.warning("auth.dispatch.invalid_token", path=path, error=str(exc), error_type=type(exc).__name__)
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid token"},
            )

        logger.info("auth.dispatch.authenticated", path=path, user_oid=user.oid)
        request.state.user = user
        return await call_next(request)
