"""FastAPI application factory.

Assembles the application by registering routers and middleware.

.. note::
   CORS is **not** configured here — it is handled at the Azure Container
   Apps ingress layer.
"""

from __future__ import annotations

from fastapi import FastAPI

from apic_vibe_portal_bff.config.settings import get_settings
from apic_vibe_portal_bff.middleware.auth import AuthMiddleware
from apic_vibe_portal_bff.middleware.error_handler import ErrorHandlerMiddleware
from apic_vibe_portal_bff.middleware.request_logger import RequestLoggerMiddleware
from apic_vibe_portal_bff.routers import api_catalog, health
from apic_vibe_portal_bff.routers.api_catalog import CatalogApiError, catalog_api_error_handler
from apic_vibe_portal_bff.utils.logger import configure_logging


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    configure_logging(log_level=settings.log_level, environment=settings.environment)

    app = FastAPI(
        title="APIC Vibe Portal BFF",
        description="Backend-for-Frontend API for the APIC Vibe Portal",
        version="0.0.0",
    )

    # --- Middleware (outermost → innermost) --------------------------------
    # Order matters: the first middleware added is outermost (processes first).
    app.add_middleware(ErrorHandlerMiddleware, debug=(settings.environment == "development"))
    app.add_middleware(RequestLoggerMiddleware)
    app.add_middleware(AuthMiddleware)

    # --- Routers -----------------------------------------------------------
    app.include_router(health.router)
    app.include_router(api_catalog.router)

    # --- Exception handlers ------------------------------------------------
    app.add_exception_handler(CatalogApiError, catalog_api_error_handler)  # type: ignore[arg-type]

    return app
