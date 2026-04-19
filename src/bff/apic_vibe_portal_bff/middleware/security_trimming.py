"""Shared FastAPI dependency factories for security-trimming integration.

Provides ``get_user_context_service()`` and ``get_accessible_api_ids()`` that
can be used as FastAPI dependencies in any router requiring security trimming.
"""

from __future__ import annotations

import logging

from apic_vibe_portal_bff.middleware.auth import AuthenticatedUser
from apic_vibe_portal_bff.middleware.rbac import get_current_user
from apic_vibe_portal_bff.services.user_context_service import UserContextService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level singleton for the UserContextService
# ---------------------------------------------------------------------------

_user_context_service_instance: UserContextService | None = None


def _get_user_context_service() -> UserContextService:
    """Return a shared :class:`UserContextService` instance.

    In production, the service is backed by Cosmos DB.  When Cosmos DB is
    not configured, a no-op repository is used that treats all APIs as public.
    Tests can override this via ``app.dependency_overrides``.
    """
    global _user_context_service_instance  # noqa: PLW0603
    if _user_context_service_instance is None:
        from apic_vibe_portal_bff.config.settings import get_settings

        settings = get_settings()

        if settings.cosmos_db_endpoint.strip():
            try:
                from azure.cosmos import CosmosClient
                from azure.identity import DefaultAzureCredential

                from apic_vibe_portal_bff.data.repositories.api_access_policy_repository import (
                    ApiAccessPolicyRepository,
                )

                credential = DefaultAzureCredential()
                cosmos_client = CosmosClient(url=settings.cosmos_db_endpoint, credential=credential)
                db = cosmos_client.get_database_client(settings.cosmos_db_database_name)
                container = db.get_container_client(settings.cosmos_db_access_policies_container)
                repo = ApiAccessPolicyRepository(container)
                _user_context_service_instance = UserContextService(policy_repository=repo)
                logger.info("UserContextService: using Cosmos DB access policy repository")
            except Exception:
                logger.exception(
                    "UserContextService: failed to create Cosmos DB repository — falling back to open access"
                )
                _user_context_service_instance = _make_open_access_service()
        else:
            logger.warning("UserContextService: Cosmos DB not configured — all APIs are publicly accessible")
            _user_context_service_instance = _make_open_access_service()

    return _user_context_service_instance


def _make_open_access_service() -> UserContextService:
    """Return a :class:`UserContextService` backed by a stub that allows all access."""
    from unittest.mock import MagicMock

    stub_repo = MagicMock()
    stub_repo.list_all_policies.return_value = []
    return UserContextService(policy_repository=stub_repo)


# ---------------------------------------------------------------------------
# FastAPI dependency functions
# ---------------------------------------------------------------------------


def get_user_context_service() -> UserContextService:
    """FastAPI dependency that returns the shared :class:`UserContextService`."""
    return _get_user_context_service()


def get_accessible_api_ids(
    user: AuthenticatedUser = get_current_user,  # type: ignore[assignment]
) -> list[str] | None:
    """FastAPI dependency: resolve the list of API IDs the current user may access.

    Returns
    -------
    None
        When the user is an admin (Portal.Admin role) — no filtering applied.
    list[str]
        The API names the user can access.  May be empty if the user belongs
        to no groups that have been granted API access.
    """

    # Note: this function is used as a Depends() target; the actual injection
    # happens in the ``_make_accessible_ids_dep`` factory below.
    svc = _get_user_context_service()
    return svc.get_accessible_api_ids(user)


def make_accessible_ids_dep():
    """Return a FastAPI dependency callable that resolves accessible API IDs.

    Usage::

        from apic_vibe_portal_bff.middleware.security_trimming import make_accessible_ids_dep

        @router.get("/api/catalog")
        def list_apis(
            accessible_ids = Depends(make_accessible_ids_dep()),
        ):
            ...
    """
    from fastapi import Depends  # noqa: PLC0415

    def _dep(user: AuthenticatedUser = Depends(get_current_user)) -> list[str] | None:  # noqa: B008
        svc = _get_user_context_service()
        return svc.get_accessible_api_ids(user)

    return _dep
