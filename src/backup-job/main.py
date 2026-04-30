"""Backup Container Apps Job — entry point.

Each invocation produces a single backup of the configured Azure API Center
service, uploads the ZIP archive to Azure Blob Storage, writes a metadata
record to Cosmos DB, and applies the configured retention policy.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from apic_client import ApiCenterDataPlaneClient
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

from apic_backup.clients.storage_client import BackupStorageClient
from apic_backup.config import get_settings
from apic_backup.models.backup_manifest import ManifestSource
from apic_backup.services.backup_service import BackupService
from apic_backup.services.metadata_service import BackupMetadataService
from apic_backup.services.retention_service import RetentionPolicy, RetentionService
from apic_backup.telemetry import configure_telemetry, get_tracer


def _add_otel_trace_context(logger: Any, method: str, event_dict: dict[str, Any]) -> dict[str, Any]:
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


# Third-party loggers that are extremely chatty at INFO/DEBUG. We pin them
# to WARNING so per-request HTTP traffic, token acquisition, etc. don't
# drown out our own structured backup_job.* events.
_NOISY_LOGGERS: tuple[str, ...] = (
    "azure",
    "azure.core.pipeline.policies.http_logging_policy",
    "azure.identity",
    "azure.cosmos",
    "azure.storage",
    "azure.monitor.opentelemetry",
    "httpx",
    "httpcore",
    "urllib3",
    "opentelemetry",
)


def _silence_noisy_loggers() -> None:
    for noisy in _NOISY_LOGGERS:
        logging.getLogger(noisy).setLevel(logging.WARNING)


def _configure_logging(log_level: str) -> None:
    resolved_level = getattr(logging, log_level.upper(), logging.INFO)

    logging.basicConfig(level=resolved_level, format="%(message)s", stream=sys.stdout)
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

    _silence_noisy_loggers()


def run() -> None:
    """Execute a single backup + retention pass."""
    settings = get_settings()
    _configure_logging(settings.log_level)

    configure_telemetry(connection_string=settings.applicationinsights_connection_string or None)
    # configure_azure_monitor() resets log levels on the root/azure loggers,
    # so re-apply our suppressions afterwards.
    _silence_noisy_loggers()
    tracer = get_tracer()
    log = structlog.get_logger()

    log.info(
        "backup_job.starting",
        api_center_endpoint=settings.api_center_endpoint,
        backup_storage_account_url=settings.backup_storage_account_url,
        cosmos_endpoint=settings.cosmos_endpoint,
        cron_schedule=settings.backup_cron_schedule,
    )

    credential = DefaultAzureCredential(
        managed_identity_client_id=settings.azure_client_id or None,
    )

    apic_client = ApiCenterDataPlaneClient(
        base_url=settings.api_center_endpoint,
        workspace_name=settings.api_center_workspace_name,
        credential=credential,
    )

    blob_service = BlobServiceClient(
        account_url=settings.backup_storage_account_url,
        credential=credential,
    )
    container = blob_service.get_container_client(settings.backup_container_name)
    storage_client = BackupStorageClient(container)

    cosmos_client = CosmosClient(url=settings.cosmos_endpoint, credential=credential)
    cosmos_db = cosmos_client.get_database_client(settings.cosmos_database)
    cosmos_container = cosmos_db.get_container_client(settings.cosmos_backup_container)
    metadata_service = BackupMetadataService(cosmos_container)

    source = ManifestSource(
        subscriptionId=settings.apic_subscription_id,
        resourceGroup=settings.apic_resource_group,
        serviceName=settings.apic_service_name,
        location=settings.apic_location,
    )

    backup_service = BackupService(
        apic_client=apic_client,
        storage_client=storage_client,
        metadata_service=metadata_service,
        source=source,
    )

    policy = RetentionPolicy(
        hourly=settings.retention_hourly,
        daily=settings.retention_daily,
        monthly=settings.retention_monthly,
        annual=settings.retention_annual,
    )
    retention = RetentionService(metadata_service, storage_client, policy)

    with tracer.start_as_current_span("backup_job.run") as span:
        result = backup_service.run()
        span.set_attribute("backup.size_bytes", result.size_bytes)
        span.set_attribute("backup.duration_ms", result.duration_ms)
        span.set_attribute("backup.id", result.metadata.backup_id)
        log.info(
            "backup_job.completed",
            backup_id=result.metadata.backup_id,
            size_bytes=result.size_bytes,
            duration_ms=result.duration_ms,
        )

    with tracer.start_as_current_span("backup_job.retention"):
        stats = retention.apply(settings.apic_service_name)
        log.info("backup_job.retention_complete", **stats)


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).exception("Backup job failed: %s", exc)
        sys.exit(1)
