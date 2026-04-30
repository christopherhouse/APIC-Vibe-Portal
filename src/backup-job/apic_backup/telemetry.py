"""Telemetry helpers for the backup container job."""

from __future__ import annotations

import logging
import os

from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource

logger = logging.getLogger(__name__)

_SERVICE_NAME = "apic-vibe-portal-backup-job"
_SERVICE_VERSION = "0.0.0"


def configure_telemetry(*, connection_string: str | None = None) -> None:
    """Initialize Azure Monitor OpenTelemetry distro for this job."""
    conn_str = connection_string or os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING", "")
    if not conn_str or conn_str == "null":
        logger.debug("APPLICATIONINSIGHTS_CONNECTION_STRING not set — skipping OTel configuration")
        return

    try:
        from azure.monitor.opentelemetry import configure_azure_monitor

        resource = Resource.create(
            {
                SERVICE_NAME: _SERVICE_NAME,
                SERVICE_VERSION: _SERVICE_VERSION,
            }
        )
        configure_azure_monitor(connection_string=conn_str, resource=resource)
        logger.info("Azure Monitor OpenTelemetry distro configured for backup job")
    except ImportError:
        logger.warning("azure-monitor-opentelemetry not installed — skipping OTel configuration")
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to configure Azure Monitor OpenTelemetry: %s", exc)


def get_tracer(name: str = _SERVICE_NAME) -> trace.Tracer:
    return trace.get_tracer(name)
