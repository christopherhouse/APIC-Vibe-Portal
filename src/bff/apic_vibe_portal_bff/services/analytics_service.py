"""Analytics event collection and aggregation service.

Receives batches of analytics events from the frontend, enriches them with
server-side context (timestamp, hashed user ID), sanitises potential PII, and
emits them as structured log entries that are forwarded to Application Insights
via the existing OpenTelemetry pipeline.

Events are also persisted to the ``analytics-events`` Cosmos DB container via
:class:`~apic_vibe_portal_bff.data.repositories.analytics_repository.AnalyticsRepository`
when one is injected at construction time.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from apic_vibe_portal_bff.data.models.analytics import AnalyticsEventDocument
from apic_vibe_portal_bff.middleware.auth import AuthenticatedUser

if TYPE_CHECKING:
    from azure.servicebus import ServiceBusSender

    from apic_vibe_portal_bff.data.repositories.analytics_repository import AnalyticsRepository

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

    Sanitization is applied recursively so that strings nested inside
    sub-dicts and lists are also examined.  String values that match a known
    PII pattern are replaced with the literal string ``'<redacted>'``.
    Other value types are left unchanged.
    """
    return {key: _sanitize_value(value) for key, value in metadata.items()}


def _sanitize_value(value: Any) -> Any:
    """Recursively sanitize a single value."""
    if isinstance(value, str):
        return "<redacted>" if _contains_pii(value) else value
    if isinstance(value, dict):
        return {k: _sanitize_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    return value


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class AnalyticsService:
    """Service for collecting and recording analytics events.

    Analytics events arrive from the frontend as batches.  Each event is
    enriched with server-side context, emitted as a structured log entry
    captured by the OTel / Application Insights pipeline, and persisted via
    one of two paths:

    1. **Service Bus (primary)** — when a ``ServiceBusSender`` is provided,
       enriched events are batch-sent to the ``analytics-events`` topic.  A
       downstream Function App consumes them and writes to Cosmos DB.
    2. **Direct Cosmos DB (fallback)** — if Service Bus is unavailable or
       not configured, events are written directly to Cosmos via the
       repository, preserving the pre-decoupling behaviour.

    Parameters
    ----------
    repository:
        Optional :class:`~apic_vibe_portal_bff.data.repositories.analytics_repository.AnalyticsRepository`
        used to persist events to Cosmos DB (for reads and fallback writes).
    service_bus_sender:
        Optional ``ServiceBusSender`` for the analytics-events topic.
        When provided, ``record_events`` sends enriched documents to
        Service Bus instead of writing directly to Cosmos.
    """

    def __init__(
        self,
        repository: AnalyticsRepository | None = None,
        service_bus_sender: ServiceBusSender | None = None,
    ) -> None:
        self._repository = repository
        self._service_bus_sender = service_bus_sender

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
        enriched_docs: list[dict[str, Any]] = []

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

                # Build the Cosmos document for persistence (SB or direct).
                api_id = str(event_payload.get("apiId", ""))
                cosmos_metadata: dict[str, Any] = {k: v for k, v in sanitized.items() if k != "apiId"}
                if page_path:
                    cosmos_metadata["pagePath"] = page_path
                if session_id is not None:
                    cosmos_metadata["sessionId"] = session_id
                doc = AnalyticsEventDocument.new(
                    event_id=str(uuid.uuid4()),
                    event_type=event_type,
                    user_id=user_id_hash or "",
                    api_id=api_id,
                    metadata=cosmos_metadata,
                )
                enriched_docs.append(doc.to_cosmos_dict())
                recorded += 1

            except Exception:  # noqa: BLE001
                logger.warning("analytics.event.record_failed", exc_info=True)

        # --- Persist enriched documents ---
        if enriched_docs:
            self._persist_events(enriched_docs)

        return recorded

    def _persist_events(self, docs: list[dict[str, Any]]) -> None:
        """Send documents to Service Bus (primary) or Cosmos DB (fallback)."""
        if self._service_bus_sender is not None:
            try:
                self._send_to_service_bus(docs)
                return
            except Exception:  # noqa: BLE001
                logger.warning(
                    "analytics.service_bus.send_failed — falling back to direct Cosmos write",
                    exc_info=True,
                )

        # Fallback: write directly to Cosmos DB
        if self._repository is not None:
            for doc in docs:
                try:
                    self._repository.create(doc)
                except Exception:  # noqa: BLE001
                    logger.warning("analytics.cosmos.write_failed", exc_info=True)

    def _send_to_service_bus(self, docs: list[dict[str, Any]]) -> None:
        """Batch-send documents to the Service Bus topic."""
        from azure.servicebus import ServiceBusMessage

        batch = self._service_bus_sender.create_message_batch()  # type: ignore[union-attr]
        for doc in docs:
            message = ServiceBusMessage(
                body=json.dumps(doc),
                content_type="application/json",
                application_properties={"eventType": doc.get("eventType", "unknown")},
            )
            try:
                batch.add_message(message)
            except ValueError:
                # ValueError is raised for two reasons:
                # 1. Batch is full — send what we have and start a new batch.
                # 2. Single message exceeds SB max size (256 KB Standard) — in
                #    this case the retry also raises ValueError, which
                #    propagates to _persist_events and triggers Cosmos fallback.
                self._service_bus_sender.send_messages(batch)  # type: ignore[union-attr]
                batch = self._service_bus_sender.create_message_batch()  # type: ignore[union-attr]
                batch.add_message(message)
        if len(batch) > 0:
            self._service_bus_sender.send_messages(batch)  # type: ignore[union-attr]

    # ------------------------------------------------------------------
    # Aggregation queries (used by GET endpoints)
    # ------------------------------------------------------------------

    def get_summary(self, *, days: int) -> dict[str, Any]:
        """Return KPI summary: counts + trend percentages."""
        if self._repository is None:
            return self._empty_summary()

        total_users = self._repository.count_distinct_users(days=days)
        total_page_views = self._repository.count_events_by_type("page_view", days=days)
        total_searches = self._repository.count_events_by_type("search_query", days=days)
        total_chats = self._repository.count_events_by_type("chat_interaction", days=days)

        # Previous period for trend calculation
        prev_users = self._repository.count_distinct_users(days=days * 2)
        prev_page_views = self._repository.count_events_by_type("page_view", days=days * 2)
        prev_searches = self._repository.count_events_by_type("search_query", days=days * 2)
        prev_chats = self._repository.count_events_by_type("chat_interaction", days=days * 2)

        return {
            "totalUsers": total_users,
            "totalPageViews": total_page_views,
            "totalSearchQueries": total_searches,
            "totalChatInteractions": total_chats,
            "avgSessionDurationSeconds": 0.0,
            "usersTrend": _trend_pct(total_users, prev_users - total_users),
            "pageViewsTrend": _trend_pct(total_page_views, prev_page_views - total_page_views),
            "searchQueriesTrend": _trend_pct(total_searches, prev_searches - total_searches),
            "chatInteractionsTrend": _trend_pct(total_chats, prev_chats - total_chats),
        }

    def get_usage_trends(self, *, days: int, time_range: str) -> dict[str, Any]:
        """Return daily usage trend data points."""
        if self._repository is None:
            return {"range": time_range, "dataPoints": []}

        pv_daily = {r["date"]: r["count"] for r in self._repository.daily_event_counts("page_view", days=days)}
        search_daily = {r["date"]: r["count"] for r in self._repository.daily_event_counts("search_query", days=days)}
        chat_daily = {r["date"]: r["count"] for r in self._repository.daily_event_counts("chat_interaction", days=days)}
        user_daily = {r["date"]: r["count"] for r in self._repository.daily_active_users(days=days)}

        all_dates = sorted(set(pv_daily) | set(search_daily) | set(chat_daily) | set(user_daily))
        data_points = [
            {
                "date": d,
                "activeUsers": user_daily.get(d, 0),
                "pageViews": pv_daily.get(d, 0),
                "searches": search_daily.get(d, 0),
                "chatInteractions": chat_daily.get(d, 0),
            }
            for d in all_dates
        ]
        return {"range": time_range, "dataPoints": data_points}

    def get_popular_apis(self, *, days: int, limit: int = 10) -> list[dict[str, Any]]:
        """Return the most popular APIs by view count."""
        if self._repository is None:
            return []

        top_apis = self._repository.top_viewed_apis(days=days, limit=limit)
        downloads = self._repository.top_downloaded_apis(days=days)
        chat_mentions = self._repository.chat_mention_counts(days=days)

        return [
            {
                "apiId": api["apiId"],
                "apiName": api["apiId"],
                "viewCount": api.get("viewCount", 0),
                "downloadCount": downloads.get(api["apiId"], 0) if isinstance(downloads, dict) else 0,
                "chatMentionCount": chat_mentions.get(api["apiId"], 0),
            }
            for api in top_apis
        ]

    def get_search_trends(self, *, days: int) -> dict[str, Any]:
        """Return search analytics data."""
        if self._repository is None:
            return self._empty_search_trends()

        daily_volume = [
            {"date": r["date"], "queryCount": r["count"], "zeroResultCount": 0}
            for r in self._repository.search_daily_volume(days=days)
        ]

        return {
            "dailyVolume": daily_volume,
            "topQueries": [],
            "zeroResultQueries": [],
            "clickThroughRate": 0.0,
            "avgResultsPerSearch": 0.0,
            "searchModeDistribution": {"keyword": 0, "semantic": 0, "hybrid": 0},
        }

    def get_user_activity(self, *, days: int) -> dict[str, Any]:
        """Return user engagement data."""
        if self._repository is None:
            return self._empty_user_activity()

        daily_users = [{"date": r["date"], "count": r["count"]} for r in self._repository.daily_active_users(days=days)]

        feature_counts = self._repository.feature_usage_counts(days=days)

        return {
            "dailyActiveUsers": daily_users,
            "weeklyActiveUsers": [],
            "avgSessionDurationSeconds": 0.0,
            "avgPagesPerSession": 0.0,
            "returningUserRate": 0.0,
            "featureAdoption": {
                "catalog": feature_counts.get("page_view", 0),
                "search": feature_counts.get("search_query", 0),
                "chat": feature_counts.get("chat_interaction", 0),
                "compare": feature_counts.get("comparison_made", 0),
                "governance": feature_counts.get("governance_viewed", 0),
            },
        }

    @staticmethod
    def _empty_summary() -> dict[str, Any]:
        return {
            "totalUsers": 0,
            "totalPageViews": 0,
            "totalSearchQueries": 0,
            "totalChatInteractions": 0,
            "avgSessionDurationSeconds": 0.0,
            "usersTrend": 0.0,
            "pageViewsTrend": 0.0,
            "searchQueriesTrend": 0.0,
            "chatInteractionsTrend": 0.0,
        }

    @staticmethod
    def _empty_search_trends() -> dict[str, Any]:
        return {
            "dailyVolume": [],
            "topQueries": [],
            "zeroResultQueries": [],
            "clickThroughRate": 0.0,
            "avgResultsPerSearch": 0.0,
            "searchModeDistribution": {"keyword": 0, "semantic": 0, "hybrid": 0},
        }

    @staticmethod
    def _empty_user_activity() -> dict[str, Any]:
        return {
            "dailyActiveUsers": [],
            "weeklyActiveUsers": [],
            "avgSessionDurationSeconds": 0.0,
            "avgPagesPerSession": 0.0,
            "returningUserRate": 0.0,
            "featureAdoption": {
                "catalog": 0,
                "search": 0,
                "chat": 0,
                "compare": 0,
                "governance": 0,
            },
        }


def _trend_pct(current: int, previous: int) -> float:
    """Calculate percentage change from *previous* to *current*."""
    if previous == 0:
        return 0.0
    return round(((current - previous) / previous) * 100, 1)
