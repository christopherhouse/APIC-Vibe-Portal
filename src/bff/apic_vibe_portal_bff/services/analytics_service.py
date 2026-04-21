"""Analytics event collection and aggregation service.

Receives batches of analytics events from the frontend, enriches them with
server-side context (timestamp, hashed user ID), sanitises potential PII, and
emits them as structured log entries that are forwarded to Application Insights
via the existing OpenTelemetry pipeline.

A future iteration can additionally persist events to Cosmos DB for queryable
analytics dashboards (task 029+).
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import UTC, datetime
from typing import Any

from apic_vibe_portal_bff.middleware.auth import AuthenticatedUser

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PII detection
# ---------------------------------------------------------------------------

# Patterns that indicate a string value is likely to contain PII.
_PII_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"),  # email address
    re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"),  # phone number (US format)
]


def _contains_pii(value: str) -> bool:
    """Return ``True`` if *value* appears to contain PII."""
    return any(p.search(value) for p in _PII_PATTERNS)


# ---------------------------------------------------------------------------
# Hashing helpers
# ---------------------------------------------------------------------------


def hash_user_id(user_id: str, salt: str = "") -> str:
    """Return a deterministic SHA-256 hex digest of *user_id*.

    Parameters
    ----------
    user_id:
        Raw user identifier (OID from Entra ID).  Never stored directly.
    salt:
        Optional pepper value mixed into the hash to prevent pre-computation
        attacks.  Supply a stable per-deployment secret when available.
    """
    raw = f"{salt}{user_id}"
    return hashlib.sha256(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Sanitisation
# ---------------------------------------------------------------------------


def sanitize_event_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of *metadata* with PII-containing string values redacted.

    String values that match a known PII pattern are replaced with the literal
    string ``'<redacted>'``.  Other value types are left unchanged.
    """
    cleaned: dict[str, Any] = {}
    for key, value in metadata.items():
        if isinstance(value, str) and _contains_pii(value):
            cleaned[key] = "<redacted>"
        else:
            cleaned[key] = value
    return cleaned


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class AnalyticsService:
    """Service for collecting and recording analytics events.

    Analytics events arrive from the frontend as batches.  Each event is
    enriched with server-side context and emitted as a structured log entry.
    The log entries are captured by the OTel / Application Insights pipeline
    configured in :mod:`apic_vibe_portal_bff.telemetry.otel_setup`.
    """

    def record_events(
        self,
        events: list[dict[str, Any]],
        user: AuthenticatedUser | None = None,
    ) -> int:
        """Record a batch of analytics event envelopes.

        Each envelope is expected to contain:

        - ``event`` — the event payload (dict with a ``type`` key)
        - ``clientTimestamp`` — ISO-8601 timestamp from the client
        - ``pagePath`` — the page route where the event occurred
        - ``sessionId`` — optional anonymised session identifier

        Parameters
        ----------
        events:
            List of raw event envelopes deserialized from the request body.
        user:
            The authenticated user submitting the events.  When provided, a
            hashed version of ``user.oid`` is included in the log entry.
            The raw OID is never stored.

        Returns
        -------
        int
            Number of events successfully recorded.
        """
        user_id_hash = hash_user_id(user.oid) if user else None
        recorded = 0

        for envelope in events:
            try:
                event_payload: dict[str, Any] = envelope.get("event") or {}
                event_type: str = str(event_payload.get("type", "unknown"))
                client_timestamp: str = str(envelope.get("clientTimestamp", ""))
                page_path: str = str(envelope.get("pagePath", ""))
                session_id: str | None = envelope.get("sessionId")

                # Build a sanitised copy of the event payload to log.
                sanitized: dict[str, Any] = sanitize_event_metadata(
                    {k: v for k, v in event_payload.items() if k != "type"}
                )

                extra: dict[str, Any] = {
                    "event_type": event_type,
                    "client_timestamp": client_timestamp,
                    "page_path": page_path,
                    "server_timestamp": datetime.now(UTC).isoformat(),
                    **sanitized,
                }
                if user_id_hash is not None:
                    extra["user_id_hash"] = user_id_hash
                if session_id is not None:
                    extra["session_id"] = session_id

                logger.info("analytics.event", extra=extra)
                recorded += 1

            except Exception:  # noqa: BLE001
                logger.warning("analytics.event.record_failed", exc_info=True)

        return recorded
