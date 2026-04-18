"""FastAPI application factory.

Assembles the application by registering routers and middleware.

.. note::
   CORS is **not** configured here — it is handled at the Azure Container
   Apps ingress layer.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from apic_vibe_portal_bff.config.settings import get_settings
from apic_vibe_portal_bff.middleware.auth import AuthMiddleware
from apic_vibe_portal_bff.middleware.error_handler import ErrorHandlerMiddleware
from apic_vibe_portal_bff.middleware.request_logger import RequestLoggerMiddleware
from apic_vibe_portal_bff.routers import api_catalog, health, search
from apic_vibe_portal_bff.routers.api_catalog import CatalogApiError, catalog_api_error_handler
from apic_vibe_portal_bff.routers.search import SearchApiError, search_api_error_handler
from apic_vibe_portal_bff.utils.logger import configure_logging

logger = logging.getLogger(__name__)


def _run_cache_warmer(interval_seconds: int) -> None:
    """Background loop that pre-populates the catalog cache on startup and
    then refreshes it periodically so user requests almost always hit Redis.

    Parameters
    ----------
    interval_seconds:
        Seconds to sleep between warm-up runs.  When 0 only the initial
        startup warm is performed.
    """
    from apic_vibe_portal_bff.routers.api_catalog import _get_service

    # Initial warm — run immediately so the cache is hot before the first
    # user request arrives.
    try:
        count = _get_service().warm_cache()
        logger.info("Startup cache warm complete", extra={"api_count": count})
    except Exception as exc:  # noqa: BLE001
        logger.warning("Startup cache warm failed: %s", exc)

    if interval_seconds <= 0:
        return

    while True:
        time.sleep(interval_seconds)
        try:
            count = _get_service().warm_cache()
            logger.debug("Periodic cache refresh complete", extra={"api_count": count})
        except Exception as exc:  # noqa: BLE001
            logger.warning("Periodic cache refresh failed: %s", exc)


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """FastAPI lifespan handler — starts the background cache-warmer thread."""
    settings = get_settings()
    thread = threading.Thread(
        target=_run_cache_warmer,
        args=(settings.cache_warm_interval_seconds,),
        daemon=True,
        name="cache-warmer",
    )
    thread.start()
    logger.info(
        "Cache warmer started",
        extra={"interval_seconds": settings.cache_warm_interval_seconds},
    )
    yield


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
    app.add_middleware(ErrorHandlerMiddleware, debug=(settings.environment == "development"))
    app.add_middleware(RequestLoggerMiddleware)
    app.add_middleware(AuthMiddleware)

    # --- Routers -----------------------------------------------------------
    app.include_router(health.router)
    app.include_router(api_catalog.router)
    app.include_router(search.router)

    # --- Exception handlers ------------------------------------------------
    app.add_exception_handler(CatalogApiError, catalog_api_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(SearchApiError, search_api_error_handler)  # type: ignore[arg-type]

    return app
