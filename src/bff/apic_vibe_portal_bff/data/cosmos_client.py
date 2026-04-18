"""Cosmos DB client initialisation.

Provides a singleton ``CosmosClient`` authenticated via
``DefaultAzureCredential`` (managed identity in production, developer
credential chain locally).  The client is created lazily on first access
and cached for the lifetime of the process.
"""

from __future__ import annotations

import logging

from azure.cosmos import CosmosClient
from azure.cosmos.container import ContainerProxy
from azure.cosmos.database import DatabaseProxy
from azure.identity import DefaultAzureCredential

from apic_vibe_portal_bff.config.settings import get_settings

logger = logging.getLogger(__name__)

# Module-level singleton — created on first call, reused thereafter.
_cosmos_client: CosmosClient | None = None


def get_cosmos_client() -> CosmosClient:
    """Return a cached :class:`CosmosClient`.

    Uses ``DefaultAzureCredential`` for Entra-ID-based auth (no access keys).

    Raises ``ValueError`` when ``COSMOS_DB_ENDPOINT`` is missing or blank so
    misconfiguration fails with a clear message before the Azure SDK client is
    constructed.
    """
    global _cosmos_client  # noqa: PLW0603
    if _cosmos_client is None:
        settings = get_settings()
        endpoint = settings.cosmos_db_endpoint.strip()
        if not endpoint:
            msg = "COSMOS_DB_ENDPOINT must be configured before creating the Cosmos DB client."
            raise ValueError(msg)
        credential = DefaultAzureCredential()
        logger.info("Creating Cosmos DB client for endpoint %s", endpoint)
        _cosmos_client = CosmosClient(url=endpoint, credential=credential)
    return _cosmos_client


def get_database() -> DatabaseProxy:
    """Return a :class:`DatabaseProxy` for the portal database."""
    settings = get_settings()
    return get_cosmos_client().get_database_client(settings.cosmos_db_database_name)


def get_container(container_name: str) -> ContainerProxy:
    """Return a :class:`ContainerProxy` for *container_name*."""
    return get_database().get_container_client(container_name)
