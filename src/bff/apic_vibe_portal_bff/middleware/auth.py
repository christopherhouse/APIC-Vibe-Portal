"""Authentication middleware placeholder.

This middleware is a pass-through stub.  Entra ID (Azure AD) integration
will be implemented in task 016 (Entra ID Authentication Integration).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware

from apic_vibe_portal_bff.utils.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

    from starlette.requests import Request
    from starlette.responses import Response

logger = get_logger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """Placeholder auth middleware — passes all requests through.

    In task 016 this will validate Entra ID tokens and set
    ``request.state.user_id`` for downstream use.
    """

    async def dispatch(self, request: Request, call_next: Callable[..., Response]) -> Response:
        """Pass through — no authentication enforced yet."""
        # TODO: Validate Entra ID bearer token (task 016)
        return await call_next(request)
