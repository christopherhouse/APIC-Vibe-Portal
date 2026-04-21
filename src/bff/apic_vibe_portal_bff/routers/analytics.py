"""Analytics dashboard API routes.

Provides read-only aggregation endpoints for the analytics dashboard UI.
All endpoints require the ``Portal.Admin`` or ``Portal.Maintainer`` role.

Endpoints
---------
GET /api/analytics/summary          - KPI summary for the selected time range
GET /api/analytics/usage-trends     - Daily usage trend data points
GET /api/analytics/popular-apis     - Most viewed / downloaded APIs
GET /api/analytics/search-trends    - Search query volume and effectiveness
GET /api/analytics/user-activity    - Active users and feature adoption
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends

from apic_vibe_portal_bff.middleware.auth import AuthenticatedUser
from apic_vibe_portal_bff.middleware.rbac import require_any_role

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# Roles that may access the analytics dashboard
_ANALYTICS_ROLES = ["Portal.Admin", "Portal.Maintainer"]

# Re-usable dependency that enforces analytics role
_require_analytics_role = require_any_role(_ANALYTICS_ROLES)

AnalyticsUserDep = Annotated[AuthenticatedUser, Depends(_require_analytics_role)]

TimeRange = Literal["7d", "30d", "90d", "1y"]

_RANGE_DAYS: dict[str, int] = {
    "7d": 7,
    "30d": 30,
    "90d": 90,
    "1y": 365,
}


def _range_days(time_range: str) -> int:
    return _RANGE_DAYS.get(time_range, 30)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


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
