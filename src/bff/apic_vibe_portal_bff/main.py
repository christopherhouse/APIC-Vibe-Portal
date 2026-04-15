"""Application entry point for Uvicorn.

Usage::

    uv run uvicorn apic_vibe_portal_bff.main:app --reload
"""

from apic_vibe_portal_bff.app import create_app

app = create_app()
