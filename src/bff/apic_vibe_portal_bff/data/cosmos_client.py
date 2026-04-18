"""Cosmos DB client initialisation.

Provides a singleton ``CosmosClient`` authenticated via
``DefaultAzureCredential`` (managed identity in production, developer
credential chain locally).  The client is created lazily on first access
and cached for the lifetime of the process.
"""

from __future__ import annotations

import functools
import logging

from azure.cosmos import CosmosClient
from azure.cosmos.container import ContainerProxy
from azure.cosmos.database import DatabaseProxy
from azure.identity import DefaultAzureCredential

from apic_vibe_portal_bff.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def get_cosmos_client(settings: Settings | None = None) -> CosmosClient:
    """Return a cached :class:`CosmosClient`.

    Uses ``DefaultAzureCredential`` for Entra-ID-based auth (no access keys).
    If ``COSMOS_DB_ENDPOINT`` is empty the client is still created but will
    fail on first data-plane call — this mirrors the local-dev fallback
    pattern used elsewhere in the BFF.
    """
    if settings is None:
        settings = get_settings()
    credential = DefaultAzureCredential()
    logger.info("Creating Cosmos DB client for endpoint %s", settings.cosmos_db_endpoint)
    return CosmosClient(url=settings.cosmos_db_endpoint, credential=credential)


def get_database(settings: Settings | None = None) -> DatabaseProxy:
    """Return a :class:`DatabaseProxy` for the portal database."""
    if settings is None:
        settings = get_settings()
    return get_cosmos_client(settings).get_database_client(settings.cosmos_db_database_name)


def get_container(container_name: str, settings: Settings | None = None) -> ContainerProxy:
    """Return a :class:`ContainerProxy` for *container_name*."""
    return get_database(settings).get_container_client(container_name)
