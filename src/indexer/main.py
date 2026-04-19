"""Azure AI Search indexing container job — entry point.

This module is the main entry point for the Azure Container Apps Job that
reindexes API Center data into Azure AI Search.  It is invoked by the Azure
Container Apps scheduler on the cron schedule defined by the
``REINDEX_CRON_SCHEDULE`` environment variable (default: ``*/5 * * * *``).

Each invocation performs a full reindex: it fetches all APIs from Azure API
Center via the **data-plane** REST API, generates embeddings via Azure OpenAI,
and upserts them into the configured AI Search index.  The process exits with
code 0 on success or non-zero on failure.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from apic_client import ApiCenterDataPlaneClient
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from openai import AzureOpenAI

from indexer.config import get_settings
from indexer.embedding_service import EmbeddingService
from indexer.index_schema import build_index_schema
from indexer.indexer_service import IndexerService
from indexer.telemetry import configure_telemetry, get_tracer


def _add_otel_trace_context(logger: Any, method: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Inject the current OTel trace_id and span_id into the log record."""
    try:
        from opentelemetry import trace as otel_trace

        span = otel_trace.get_current_span()
        ctx = span.get_span_context()
        if ctx and ctx.is_valid:
            event_dict["trace_id"] = format(ctx.trace_id, "032x")
            event_dict["span_id"] = format(ctx.span_id, "016x")
    except Exception:  # noqa: BLE001
        pass
    return event_dict


def _configure_logging(log_level: str) -> None:
    resolved_level = getattr(logging, log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=resolved_level,
        format="%(message)s",
        stream=sys.stdout,
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _add_otel_trace_context,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(resolved_level),
    )

    # Silence noisy Azure SDK HTTP pipeline loggers.
    for azure_logger_name in (
        "azure.core.pipeline.policies.http_logging_policy",
        "azure.identity",
        "httpx",
    ):
        logging.getLogger(azure_logger_name).setLevel(logging.WARNING)


def run() -> None:
    """Execute a full reindex and exit."""
    settings = get_settings()
    _configure_logging(settings.log_level)

    # Initialise telemetry before any Azure SDK calls so that all outbound
    # HTTP spans are captured automatically.
    configure_telemetry(connection_string=settings.applicationinsights_connection_string or None)

    tracer = get_tracer()
    log = structlog.get_logger()
    log.info(
        "Indexer job starting",
        index=settings.ai_search_index_name,
        endpoint=settings.api_center_endpoint,
        cron_schedule=settings.reindex_cron_schedule,
    )

    # Pin to the UAMI client ID when running in Azure so that the credential does
    # not accidentally resolve a different managed identity on the host.  In local
    # development (AZURE_CLIENT_ID is empty) the full DefaultAzureCredential chain
    # is used (Azure CLI, VS Code, etc.).
    credential = DefaultAzureCredential(
        managed_identity_client_id=settings.azure_client_id or None,
    )

    # --- Azure API Center data-plane client ------------------------------
    apic_client = ApiCenterDataPlaneClient(
        base_url=settings.api_center_endpoint,
        workspace_name=settings.api_center_workspace_name,
        credential=credential,
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
        index_name=settings.ai_search_index_name,
        workspace_name=settings.api_center_workspace_name,
    )

    with tracer.start_as_current_span("indexer.full_reindex") as span:
        # --- Ensure index schema is up to date --------------------------------
        schema = build_index_schema(
            index_name=settings.ai_search_index_name,
            embedding_dimensions=settings.openai_embedding_dimensions,
        )
        indexer.ensure_index(schema)

        # --- Run full reindex ------------------------------------------------
        count = indexer.full_reindex()
        span.set_attribute("indexer.documents_indexed", count)
        log.info("Indexer job complete", documents_indexed=count)


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).exception("Indexer job failed: %s", exc)
        sys.exit(1)
