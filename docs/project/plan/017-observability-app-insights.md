# 017 - Phase 1 MVP: Application Insights Observability

## References
- [Architecture Document](../apic_architecture.md) — Observability: App Insights
- [Product Charter](../apic_product_charter.md) — Operational excellence; success metrics tracking
- [Product Spec](../apic_portal_spec.md) — Monitoring and diagnostics requirements

## Overview
Integrate Azure Application Insights across both the frontend and BFF for comprehensive observability: distributed tracing, custom metrics, error tracking, and operational dashboards.

## Dependencies
- **002** — Azure infrastructure (App Insights resource deployed)
- **004** — Frontend project setup
- **005** — BFF API project setup

## Implementation Details

### 1. BFF Instrumentation
```
src/bff/src/
├── telemetry/
│   ├── app-insights.ts         # App Insights initialization
│   ├── custom-metrics.ts       # Custom metric definitions
│   └── correlation.ts          # Request correlation middleware
```

- Use `applicationinsights` npm package
- Initialize before Express app starts
- Auto-collect: requests, dependencies, exceptions, performance
- Add correlation ID middleware (propagate from frontend)
- Custom metrics:
  - `api_center_requests` — Calls to API Center with duration
  - `search_queries` — Search requests with duration and result count
  - `chat_messages` — Chat interactions with duration
  - `cache_hits` / `cache_misses` — Cache effectiveness
  - `auth_failures` — Failed authentication attempts

### 2. BFF Structured Logging Enhancement
- Integrate logger (from task 005) with App Insights
- Trace-level logs for debugging
- Include correlation ID in all log entries
- Log critical operations: search queries, chat completions, auth events

### 3. Frontend Telemetry
```
src/frontend/lib/
├── telemetry/
│   ├── app-insights-browser.ts  # Browser SDK initialization
│   ├── use-tracking.ts          # Custom hook for tracking
│   └── track-events.ts          # Typed event tracking functions
```

- Use `@microsoft/applicationinsights-web` browser SDK
- Configure with connection string from environment
- Auto-collect: page views, exceptions, AJAX dependencies
- Custom events:
  - `search_performed` — Query text, result count, duration
  - `api_viewed` — API ID, source (catalog, search, chat)
  - `chat_message_sent` — Message length, session ID
  - `filter_applied` — Filter type and value
  - `spec_downloaded` — API ID, format

### 4. Distributed Tracing
- Generate correlation ID on frontend
- Pass in `x-correlation-id` header to BFF
- BFF propagates to Azure service calls
- End-to-end trace visibility in Application Insights

### 5. Error Tracking
- Frontend: Catch unhandled errors and promise rejections
- BFF: Catch unhandled exceptions in error middleware
- Include context: user ID, page URL, request path
- Alert on error rate spikes (configure in App Insights)

### 6. Health Dashboard (Bicep/ARM)
Define an App Insights workbook or dashboard:
- Request rate and latency (BFF)
- Error rate and top errors
- Search query volume and latency
- Chat usage metrics
- Frontend page load times
- Dependency health (API Center, AI Search, OpenAI)

### 7. Availability Tests
- Configure availability ping tests for:
  - Frontend health endpoint
  - BFF `/health` endpoint
  - BFF `/health/ready` endpoint

## Testing & Acceptance Criteria
- [ ] BFF sends telemetry to Application Insights (requests, dependencies, exceptions)
- [ ] Frontend sends page views and custom events to Application Insights
- [ ] Correlation ID propagates from frontend through BFF to Azure services
- [ ] Custom metrics (search, chat, cache) are recorded correctly
- [ ] Structured logs include correlation IDs
- [ ] Unhandled errors in both frontend and BFF are captured
- [ ] Health dashboard shows key operational metrics
- [ ] Availability tests run and report correctly
- [ ] Telemetry initialization doesn't impact application startup time
- [ ] Unit tests verify custom metric recording (with mocked telemetry client)

## Coding Agent Prompt

> **Task**: Implement plan step 017 — Application Insights Observability.
>
> Read the full task specification at `docs/project/plan/017-observability-app-insights.md`.
>
> Reference the architecture at `docs/project/apic_architecture.md` (Observability: App Insights) and `docs/project/plan/002-sprint-zero-azure-infra-bicep.md` for the App Insights resource.
>
> In the BFF, integrate the `applicationinsights` SDK with auto-collection, custom metrics (search, chat, cache, auth), correlation ID middleware, and enhanced structured logging. In the frontend, integrate the browser Application Insights SDK with page views, custom events, and error tracking. Implement distributed tracing via correlation ID propagation.
>
> Write tests verifying custom metrics are recorded. Verify the build succeeds and all tests pass.
