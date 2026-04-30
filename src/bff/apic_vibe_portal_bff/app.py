"""FastAPI application factory.

Assembles the application by registering routers and middleware.

.. note::
   CORS is **not** configured here — it is handled at the Azure Container
   Apps ingress layer.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from apic_vibe_portal_bff.config.settings import get_settings
from apic_vibe_portal_bff.middleware.auth import AuthMiddleware
from apic_vibe_portal_bff.middleware.error_handler import ErrorHandlerMiddleware
from apic_vibe_portal_bff.middleware.request_logger import RequestLoggerMiddleware
from apic_vibe_portal_bff.routers import api_catalog, chat, health, search
from apic_vibe_portal_bff.routers.admin_access_policies import router as admin_access_policies_router
from apic_vibe_portal_bff.routers.admin_agents import router as admin_agents_router
from apic_vibe_portal_bff.routers.analytics import close_analytics_service
from apic_vibe_portal_bff.routers.analytics import router as analytics_router
from apic_vibe_portal_bff.routers.api_catalog import CatalogApiError, catalog_api_error_handler
from apic_vibe_portal_bff.routers.api_compare import router as compare_router
from apic_vibe_portal_bff.routers.backup import router as backup_router
from apic_vibe_portal_bff.routers.chat import ChatApiError, chat_api_error_handler
from apic_vibe_portal_bff.routers.governance import router as governance_router
from apic_vibe_portal_bff.routers.mcp_inspector import McpInspectorError, mcp_inspector_error_handler
from apic_vibe_portal_bff.routers.mcp_inspector import router as mcp_inspector_router
from apic_vibe_portal_bff.routers.metadata import router as metadata_router
from apic_vibe_portal_bff.routers.search import SearchApiError, search_api_error_handler
from apic_vibe_portal_bff.telemetry.middleware import OTelEnrichmentMiddleware
from apic_vibe_portal_bff.telemetry.otel_setup import configure_telemetry
from apic_vibe_portal_bff.utils.logger import configure_logging

logger = logging.getLogger(__name__)


def _run_startup_cache_warm() -> None:
    """Warm the catalog cache once at startup.

    Runs in a background thread so it doesn't block the server from
    accepting requests.  Ongoing freshness is maintained by the
    stale-while-revalidate logic in :class:`ApiCatalogService`.
    """
    from apic_vibe_portal_bff.routers.api_catalog import _get_service

    try:
        count = _get_service().warm_cache()
        logger.info("Startup catalog cache warm complete", extra={"api_count": count})
    except Exception as exc:  # noqa: BLE001
        logger.warning("Startup catalog cache warm failed: %s", exc)


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """FastAPI lifespan handler — configures telemetry and starts the cache-warm thread."""
    settings = get_settings()
    configure_telemetry(
        connection_string=settings.applicationinsights_connection_string or None,
        environment=settings.environment,
    )

    thread = threading.Thread(
        target=_run_startup_cache_warm,
        daemon=True,
        name="cache-warmer",
    )
    thread.start()
    logger.info("Startup cache warm thread started")
    yield
    # --- Shutdown ---
    close_analytics_service()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    configure_logging(log_level=settings.log_level, environment=settings.environment)

    app = FastAPI(
        title="APIC Vibe Portal BFF",
        description="Backend-for-Frontend API for the APIC Vibe Portal",
        version="0.0.0",
        lifespan=_lifespan,
    )

    # --- Middleware (outermost → innermost) --------------------------------
    # Order matters: the first middleware added is outermost (processes first).
    # NOTE: GZip compression is intentionally omitted — Azure Container Apps
    # ingress handles response compression.  Adding GZipMiddleware here causes
    # double-compression (BFF gzips, then ACA ingress gzips again), resulting
    # in ERR_CONTENT_DECODING_FAILED in the browser.
    app.add_middleware(ErrorHandlerMiddleware, debug=(settings.environment == "development"))
    app.add_middleware(OTelEnrichmentMiddleware)
    app.add_middleware(RequestLoggerMiddleware)
    app.add_middleware(AuthMiddleware)

    # --- Routers -----------------------------------------------------------
    app.include_router(health.router)
    app.include_router(api_catalog.router)
    app.include_router(search.router)
    app.include_router(chat.router)
    app.include_router(admin_access_policies_router)
    app.include_router(admin_agents_router)
    app.include_router(backup_router)
    app.include_router(compare_router)
    app.include_router(governance_router)
    app.include_router(analytics_router)
    app.include_router(metadata_router)
    app.include_router(mcp_inspector_router)

    # --- Exception handlers ------------------------------------------------
    app.add_exception_handler(CatalogApiError, catalog_api_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(SearchApiError, search_api_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ChatApiError, chat_api_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(McpInspectorError, mcp_inspector_error_handler)  # type: ignore[arg-type]

    return app
