"""Azure AI Search indexing container job — entry point.

This module is the main entry point for the Azure Container Apps Job that
reindexes API Center data into Azure AI Search.  It is invoked by the Azure
Container Apps scheduler on the cron schedule defined by the
``REINDEX_CRON_SCHEDULE`` environment variable (default: ``*/5 * * * *``).

Each invocation performs a full reindex: it fetches all APIs from Azure API
Center, generates embeddings via Azure OpenAI, and upserts them into the
configured AI Search index.  The process exits with code 0 on success or
non-zero on failure, which Azure Container Apps Jobs use to determine
retry/failure behaviour.
"""

from __future__ import annotations

import logging
import sys

import structlog
from azure.identity import DefaultAzureCredential
from azure.mgmt.apicenter import ApiCenterMgmtClient
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from openai import AzureOpenAI

from indexer.config import get_settings
from indexer.embedding_service import EmbeddingService
from indexer.index_schema import build_index_schema
from indexer.indexer_service import IndexerService


def _configure_logging(log_level: str) -> None:
    resolved_level = getattr(logging, log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=resolved_level,
        format="%(message)s",
        stream=sys.stdout,
    )
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(resolved_level),
    )

    # Silence the Azure SDK HTTP pipeline loggers — they log every single
    # HTTP request/response at INFO level which drowns out useful output.
    for azure_logger_name in (
        "azure.core.pipeline.policies.http_logging_policy",
        "azure.identity",
        "azure.mgmt.apicenter",
    ):
        logging.getLogger(azure_logger_name).setLevel(logging.WARNING)


def run() -> None:
    """Execute a full reindex and exit."""
    settings = get_settings()
    _configure_logging(settings.log_level)

    log = structlog.get_logger()
    log.info(
        "Indexer job starting",
        index=settings.ai_search_index_name,
        service=settings.api_center_service_name,
        cron_schedule=settings.reindex_cron_schedule,
    )

    # Pin to the UAMI client ID when running in Azure so that the credential does
    # not accidentally resolve a different managed identity on the host.  In local
    # development (AZURE_CLIENT_ID is empty) the full DefaultAzureCredential chain
    # is used (Azure CLI, VS Code, etc.).
    credential = DefaultAzureCredential(
        managed_identity_client_id=settings.azure_client_id or None,
    )

    # --- Azure API Center client -----------------------------------------
    apic_client = ApiCenterMgmtClient(
        credential=credential,
        subscription_id=settings.api_center_subscription_id,
    )

    # --- AI Search clients -----------------------------------------------
    search_index_client = SearchIndexClient(
        endpoint=settings.ai_search_endpoint,
        credential=credential,
    )
    search_client = SearchClient(
        endpoint=settings.ai_search_endpoint,
        index_name=settings.ai_search_index_name,
        credential=credential,
    )

    # --- Azure OpenAI client ---------------------------------------------
    openai_client = AzureOpenAI(
        azure_endpoint=settings.openai_endpoint,
        azure_deployment=settings.openai_embedding_deployment,
        api_version="2024-02-01",
        azure_ad_token_provider=lambda: credential.get_token("https://cognitiveservices.azure.com/.default").token,
    )

    # --- Services --------------------------------------------------------
    embedding_service = EmbeddingService(
        client=openai_client,
        deployment=settings.openai_embedding_deployment,
        chunk_size=settings.embedding_chunk_size,
    )

    indexer = IndexerService(
        apic_client=apic_client,
        search_index_client=search_index_client,
        search_client=search_client,
        embedding_service=embedding_service,
        resource_group=settings.api_center_resource_group,
        service_name=settings.api_center_service_name,
        index_name=settings.ai_search_index_name,
        workspace_name=settings.api_center_workspace_name,
    )

    # --- Ensure index schema is up to date --------------------------------
    schema = build_index_schema(
        index_name=settings.ai_search_index_name,
        embedding_dimensions=settings.openai_embedding_dimensions,
    )
    indexer.ensure_index(schema)

    # --- Run full reindex ------------------------------------------------
    count = indexer.full_reindex()
    log.info("Indexer job complete", documents_indexed=count)


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).exception("Indexer job failed: %s", exc)
        sys.exit(1)
