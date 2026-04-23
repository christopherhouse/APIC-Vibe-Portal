"""Analytics API routes.

Provides:
- POST /api/analytics/events  — ingest analytics events from the frontend
- GET  /api/analytics/summary          — KPI summary (admin/maintainer)
- GET  /api/analytics/usage-trends     — Daily usage trend data points
- GET  /api/analytics/popular-apis     — Most viewed / downloaded APIs
- GET  /api/analytics/search-trends    — Search query volume and effectiveness
- GET  /api/analytics/user-activity    — Active users and feature adoption

The ``POST /events`` endpoint is accessible by any authenticated user so the
frontend can submit events without requiring elevated roles.  The read
endpoints are restricted to ``Portal.Admin`` and ``Portal.Maintainer``.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, field_validator

from apic_vibe_portal_bff.config.settings import get_settings
from apic_vibe_portal_bff.middleware.auth import AuthenticatedUser
from apic_vibe_portal_bff.middleware.rbac import get_current_user, require_any_role
from apic_vibe_portal_bff.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# Roles that may access the analytics dashboard
_ANALYTICS_ROLES = ["Portal.Admin", "Portal.Maintainer"]

# Re-usable dependency that enforces analytics role
_require_analytics_role = require_any_role(_ANALYTICS_ROLES)

AnalyticsUserDep = Annotated[AuthenticatedUser, Depends(_require_analytics_role)]
AuthUserDep = Annotated[AuthenticatedUser, Depends(get_current_user)]

TimeRange = Literal["7d", "30d", "90d", "1y"]

_RANGE_DAYS: dict[str, int] = {
    "7d": 7,
    "30d": 30,
    "90d": 90,
    "1y": 365,
}


def _range_days(time_range: str) -> int:
    return _RANGE_DAYS.get(time_range, 30)


# Service singleton — created lazily on first request.
_service_instance: AnalyticsService | None = None

logger = logging.getLogger(__name__)


def _get_service() -> AnalyticsService:
    """Lazy-initialize and return the analytics service singleton.

    The :class:`~apic_vibe_portal_bff.data.repositories.analytics_repository.AnalyticsRepository`
    is wired in here so that events are persisted to Cosmos DB in addition to
    being emitted as structured log entries.

    If ``COSMOS_DB_ENDPOINT`` is not configured or the repository cannot be
    initialized, the service falls back to structured-log-only delivery so
    that analytics event ingestion degrades gracefully rather than returning
    HTTP 500 on every request.
    """
    global _service_instance  # noqa: PLW0603
    if _service_instance is None:
        settings = get_settings()
        analytics_repo = None
        if settings.cosmos_db_endpoint.strip():
            try:
                from apic_vibe_portal_bff.data.cosmos_client import get_container
                from apic_vibe_portal_bff.data.repositories.analytics_repository import AnalyticsRepository

                analytics_container = get_container(settings.cosmos_db_analytics_container)
                analytics_repo = AnalyticsRepository(analytics_container)
            except Exception:
                logger.exception("Failed to initialise analytics repository — events will be logged only")
        else:
            logger.info("COSMOS_DB_ENDPOINT not configured — analytics events will be logged only")
        _service_instance = AnalyticsService(repository=analytics_repo)
    return _service_instance


AnalyticsServiceDep = Annotated[AnalyticsService, Depends(_get_service)]


# ---------------------------------------------------------------------------
# Request / response models for POST /events
# ---------------------------------------------------------------------------


class AnalyticsEventPayload(BaseModel):
    """Raw analytics event payload.

    The schema is intentionally permissive (extra fields allowed) so that
    new event types can be added on the frontend without a BFF deploy.
    Individual string values are capped at 500 characters and the total
    number of extra keys is limited to 20 to prevent log flooding.
    """

    model_config = {"extra": "allow"}

    type: str = Field(..., max_length=64, description="Event type discriminator.")

    @field_validator("type")
    @classmethod
    def _validate_type(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Event type must be a non-empty string.")
        return v

    def model_post_init(self, __context: Any) -> None:
        """Enforce size constraints on extra fields after validation."""
        extra = self.__pydantic_extra__ or {}
        if len(extra) > 20:
            raise ValueError("Too many event payload fields (max 20 extra fields allowed).")
        for key, value in extra.items():
            if isinstance(value, str) and len(value) > 500:
                raise ValueError(f"Event payload field '{key}' exceeds maximum length of 500 characters.")


class AnalyticsEventEnvelope(BaseModel):
    """A single analytics event with client-side context metadata."""

    event: AnalyticsEventPayload
    clientTimestamp: str = Field(..., description="ISO-8601 timestamp from the client.")
    pagePath: str = Field(default="", description="Page route where the event was triggered.")
    sessionId: str | None = Field(default=None, description="Anonymised session identifier.")


class AnalyticsEventBatchRequest(BaseModel):
    """Batch of analytics events submitted from the frontend."""

    events: list[AnalyticsEventEnvelope] = Field(..., min_length=1, max_length=100)


class AnalyticsEventBatchResponse(BaseModel):
    """Response after processing an analytics event batch."""

    accepted: int
    """Number of events successfully accepted and recorded."""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post(
    "/events",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=AnalyticsEventBatchResponse,
)
async def post_analytics_events(
    body: AnalyticsEventBatchRequest,
    user: AuthUserDep,
    service: AnalyticsServiceDep,
) -> AnalyticsEventBatchResponse:
    """Accept a batch of analytics events from the frontend.

    Events are enriched with server-side context (timestamp, hashed user ID),
    recorded via the Application Insights telemetry pipeline, and persisted to
    the ``analytics-events`` Cosmos DB container.

    - Requires any authenticated user (no elevated role needed).
    - Accepts between 1 and 100 events per request.
    - Returns ``202 Accepted`` with the count of accepted events.
    """
    raw_events = [envelope.model_dump() for envelope in body.events]
    accepted = service.record_events(raw_events, user=user)
    return AnalyticsEventBatchResponse(accepted=accepted)


@router.get("/summary")
async def get_analytics_summary(
    _user: AnalyticsUserDep,
    time_range: TimeRange = "30d",
) -> dict[str, Any]:
    """Return portal KPI summary for the selected time range.

    Returns
    -------
    - totalUsers: Unique users in the period
    - totalPageViews: Total page views
    - totalSearchQueries: Total search queries
    - totalChatInteractions: Total AI chat messages
    - avgSessionDurationSeconds: Mean session duration in seconds
    - usersTrend: % change vs. previous period
    - pageViewsTrend: % change vs. previous period
    - searchQueriesTrend: % change vs. previous period
    - chatInteractionsTrend: % change vs. previous period
    """
    days = _range_days(time_range)
    # Placeholder implementation — replace with real aggregation from
    # Application Insights / Cosmos DB analytics store in task 028.
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
        "_rangeDays": days,
    }


@router.get("/usage-trends")
async def get_usage_trends(
    _user: AnalyticsUserDep,
    time_range: TimeRange = "30d",
) -> dict[str, Any]:
    """Return daily usage trend data points for the selected time range.

    Returns
    -------
    - range: The requested time range
    - dataPoints: list of {date, activeUsers, pageViews, searches, chatInteractions}
    """
    return {
        "range": time_range,
        "dataPoints": [],
    }


@router.get("/popular-apis")
async def get_popular_apis(
    _user: AnalyticsUserDep,
    time_range: TimeRange = "30d",
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Return the most viewed / downloaded APIs for the selected time range.

    Returns list of:
    - apiId: API identifier
    - apiName: API display name
    - viewCount: Number of API detail views
    - downloadCount: Number of spec downloads
    - chatMentionCount: Number of times referenced in chat
    """
    return []


@router.get("/search-trends")
async def get_search_trends(
    _user: AnalyticsUserDep,
    time_range: TimeRange = "30d",
) -> dict[str, Any]:
    """Return search analytics for the selected time range.

    Returns
    -------
    - dailyVolume: list of {date, queryCount, zeroResultCount}
    - topQueries: list of {queryHash, displayTerm, count, avgResultCount}
    - zeroResultQueries: list of {displayTerm, count}
    - clickThroughRate: % of searches leading to API views
    - avgResultsPerSearch: Mean number of results per query
    - searchModeDistribution: {keyword, semantic, hybrid} usage counts
    """
    return {
        "dailyVolume": [],
        "topQueries": [],
        "zeroResultQueries": [],
        "clickThroughRate": 0.0,
        "avgResultsPerSearch": 0.0,
        "searchModeDistribution": {"keyword": 0, "semantic": 0, "hybrid": 0},
    }


@router.get("/user-activity")
async def get_user_activity(
    _user: AnalyticsUserDep,
    time_range: TimeRange = "30d",
) -> dict[str, Any]:
    """Return user engagement data for the selected time range.

    Returns
    -------
    - dailyActiveUsers: list of {date, count}
    - weeklyActiveUsers: list of {week, count}
    - avgSessionDurationSeconds: Mean session length
    - avgPagesPerSession: Mean pages visited per session
    - returningUserRate: % of returning vs. new users
    - featureAdoption: {catalog, search, chat, compare, governance} usage counts
    """
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
