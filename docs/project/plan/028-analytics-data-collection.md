# 028 - Phase 3: Usage Analytics Data Collection

> **🔲 Status: Not Started**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References

- [Architecture Document](../apic_architecture.md) — Observability: App Insights; data collection layer
- [Product Charter](../apic_product_charter.md) — Phase 3: Analytics; success metrics (portal adoption, API discovery time)
- [Product Spec](../apic_portal_spec.md) — Analytics data requirements

## Overview

Implement a comprehensive analytics data collection layer that captures user interactions, search behavior, API usage patterns, and portal adoption metrics. This data feeds the analytics dashboards built in subsequent tasks.

## Dependencies

- **019** — Application Insights observability (telemetry foundation)
- **006** — BFF API project setup
- **008** — Entra ID authentication (user identity for analytics)

## Implementation Details

### 1. Analytics Events Model

```
src/shared/src/models/
├── analytics-event.ts             # Analytics event types
```

Define typed analytics events:

```typescript
type AnalyticsEvent =
  | { type: 'page_view'; page: string; duration?: number }
  | {
      type: 'search_query';
      queryHash: string;
      queryLength: number;
      resultCount: number;
      clickedResult?: string;
    }
  | { type: 'api_view'; apiId: string; source: 'catalog' | 'search' | 'chat' | 'compare' }
  | { type: 'spec_download'; apiId: string; format: 'json' | 'yaml' }
  | { type: 'chat_interaction'; sessionId: string; messageCount: number; agentUsed: string }
  | { type: 'comparison_made'; apiIds: string[]; usedAiAnalysis: boolean }
  | { type: 'governance_viewed'; apiId?: string; section: string }
  | { type: 'filter_applied'; filterType: string; filterValue: string; context: string }
  | { type: 'user_session'; userIdHash: string; sessionDuration: number; pagesVisited: number };
```

### 2. BFF Analytics Service

```
src/bff/src/bff/services/
├── analytics_service.py            # Analytics collection and storage
└── test_analytics_service.py
```

- Collect events from frontend via API endpoint
- Batch events for efficient storage
- Enrich events with server-side context (user ID, timestamp, correlation ID)
- Store in Application Insights custom events
- Optionally store in a dedicated analytics store (Azure Table Storage or Cosmos DB for querying)

### 3. Analytics API Endpoints

```
src/bff/src/bff/routers/
├── analytics.py                    # Analytics endpoints (FastAPI router)
└── test_analytics.py
```

| Method | Path                           | Description                       |
| ------ | ------------------------------ | --------------------------------- |
| `POST` | `/api/analytics/events`        | Batch submit analytics events     |
| `GET`  | `/api/analytics/summary`       | Get analytics summary (admin)     |
| `GET`  | `/api/analytics/search-trends` | Search query trends (admin)       |
| `GET`  | `/api/analytics/popular-apis`  | Most viewed/searched APIs (admin) |
| `GET`  | `/api/analytics/user-activity` | User activity summary (admin)     |

### 4. Frontend Analytics Hook

```
src/frontend/lib/
├── analytics/
│   ├── analytics-provider.tsx      # Analytics context provider
│   ├── use-analytics.ts           # Custom hook for tracking
│   └── event-buffer.ts            # Client-side event batching
```

- Provide `useAnalytics()` hook to all components
- Auto-track page views via Next.js router events
- Buffer events client-side and flush in batches (every 10 events or 30 seconds)
- Track search queries, API views, spec downloads automatically
- Minimal performance impact (async, non-blocking)

### 5. Privacy & Data Handling

- Hash user IDs server-side before storage (use `userIdHash` field, never raw user IDs)
- Sanitize `search_query` before persisting: redact potential PII (emails, names, IDs) using a server-side redaction utility, or store only derived aggregates (query length, token count, salted hash) instead of raw query strings
- Respect Do Not Track browser setting
- Configurable data retention period
- Data is anonymized for aggregation
- No recording of chat content (only metadata: message count, agent used)

### 6. Analytics Data Schema

Design schema for querying:

- Partition by date for time-series queries
- Index by event type for aggregation
- Index by user for activity tracking
- Index by API ID for popularity metrics

## Testing & Acceptance Criteria

- [ ] Frontend analytics hook captures page views automatically
- [ ] Search events are tracked with query and result count
- [ ] API view events capture source (catalog, search, chat)
- [ ] Events are batched and submitted efficiently
- [ ] BFF analytics service stores events correctly
- [ ] Admin analytics endpoints return aggregated data
- [ ] Privacy controls work (Do Not Track, anonymization)
- [ ] Event buffer flushes on page unload
- [ ] Unit tests cover event collection, batching, and storage
- [ ] Performance impact of analytics is negligible (< 10ms per event)

## Implementation Notes

<!--
  This section is a living record updated by the implementing agent.
  Update status, log decisions, and record validation results as work progresses.
  When complete, change the Status at the top of this document to ✅ Complete.
-->

### Status History

| Date | Status         | Author | Notes        |
| ---- | -------------- | ------ | ------------ |
| —    | 🔲 Not Started | —      | Task created |

### Technical Decisions

_No technical decisions recorded yet._

### Deviations from Plan

_No deviations from the original plan._

### Validation Results

_No validation results yet._

## Coding Agent Prompt

```text
**Task**: Implement plan step 028 — Usage Analytics Data Collection.

Read the full task specification at `docs/project/plan/028-analytics-data-collection.md`.

Reference `docs/project/plan/019-observability-app-insights.md` for the existing telemetry foundation and `docs/project/plan/008-entra-id-authentication.md` for user identity.

Create typed analytics event models in the shared package. In the BFF, create an analytics service for event storage and admin query endpoints. In the frontend, create an analytics provider with a useAnalytics hook, automatic page view tracking, event batching, and privacy controls.

Write unit tests for event collection, batching, storage, and aggregation using pytest (BFF) and Jest (frontend). Verify all tests pass.

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/028-analytics-data-collection.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
