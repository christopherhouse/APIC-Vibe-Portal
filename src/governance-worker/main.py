"""Governance snapshot container job — entry point.

This module is the main entry point for the Azure Container Apps Job that
scans all APIs in Azure API Center, evaluates each one against the
governance rules engine, and persists point-in-time governance snapshot
documents in Azure Cosmos DB.

Each invocation performs a full scan: every API in the configured workspace
is fetched, enriched with version and deployment data, evaluated against
the 13 built-in governance rules, and upserted as a snapshot document in the
``governance-snapshots`` Cosmos DB container.  Snapshots are keyed by
``{api_id}-{today}`` so the job is idempotent — running it multiple times
per day overwrites the earlier snapshot for that date.

The job exits with code 0 on success or non-zero on failure.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from apic_client import ApiCenterDataPlaneClient
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential

from governance_worker.config import get_settings
from governance_worker.scanner import GovernanceScannerService
from governance_worker.telemetry import configure_telemetry, get_tracer


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

    for azure_logger_name in (
        "azure.core.pipeline.policies.http_logging_policy",
        "azure.identity",
        "httpx",
    ):
        logging.getLogger(azure_logger_name).setLevel(logging.WARNING)


def run() -> None:
    """Execute a full governance scan and exit."""
    settings = get_settings()
    _configure_logging(settings.log_level)

    configure_telemetry(connection_string=settings.applicationinsights_connection_string or None)

    tracer = get_tracer()
    log = structlog.get_logger()
    log.info(
        "governance_worker.starting",
        cosmos_endpoint=settings.cosmos_db_endpoint,
        api_center_endpoint=settings.api_center_endpoint,
        container=settings.cosmos_db_governance_container,
        cron_schedule=settings.scan_cron_schedule,
    )

    # Pin to the UAMI client ID when running in Azure so DefaultAzureCredential
    # does not accidentally resolve a different managed identity.
    credential = DefaultAzureCredential(
        managed_identity_client_id=settings.azure_client_id or None,
    )

    apic_client = ApiCenterDataPlaneClient(
        base_url=settings.api_center_endpoint,
        workspace_name=settings.api_center_workspace_name,
        credential=credential,
    )

    cosmos_client = CosmosClient(
        url=settings.cosmos_db_endpoint,
        credential=credential,
    )

    scanner = GovernanceScannerService(
        apic_client=apic_client,
        cosmos_client=cosmos_client,
        database_name=settings.cosmos_db_database_name,
        container_name=settings.cosmos_db_governance_container,
        workspace_name=settings.api_center_workspace_name,
        agent_id=settings.agent_id,
    )

    with tracer.start_as_current_span("governance_worker.full_scan") as span:
        count = scanner.scan_all()
        span.set_attribute("governance_worker.apis_scanned", count)
        log.info("governance_worker.complete", apis_scanned=count)


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).exception("Governance worker failed: %s", exc)
        sys.exit(1)
