# 019 - Phase 1 MVP: End-to-End OpenTelemetry Observability (Azure Monitor)

> **✅ Status: Complete**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References

- [Architecture Document](../apic_architecture.md) — Observability: App Insights
- [Product Charter](../apic_product_charter.md) — Operational excellence; success metrics tracking
- [Product Spec](../apic_portal_spec.md) — Monitoring and diagnostics requirements
- [Azure Monitor OpenTelemetry Distro](https://learn.microsoft.com/en-us/azure/azure-monitor/app/opentelemetry-enable?tabs=python) — Python SDK

## Overview

Implement end-to-end OpenTelemetry observability using the **Azure Monitor OpenTelemetry Distro** (`azure-monitor-opentelemetry` for the BFF, `@microsoft/applicationinsights-web` for the browser frontend). This gives us distributed tracing with W3C Trace Context correlation, custom OTel metrics for usage measurement, structured logging, and automatic App Insights integration — all from a single instrumentation layer.

## Dependencies

- **002** — Azure infrastructure (App Insights resource deployed)
- **005** — Frontend project setup
- **006** — BFF API project setup

## Implementation Details

### 1. BFF — Azure Monitor OpenTelemetry Distro Setup

```
src/bff/src/bff/
├── telemetry/
│   ├── __init__.py
│   ├── otel_setup.py           # Azure Monitor OTel distro initialization
│   ├── metrics.py              # Custom OTel meter & metric definitions
│   ├── token_metrics.py        # Token usage metric helpers (tiktoken + actuals)
│   └── middleware.py           # OTel-aware request middleware
```

**Initialization (`otel_setup.py`)**

- Use `azure-monitor-opentelemetry` distro — single call to `configure_azure_monitor()` to wire up traces, metrics, and logs to App Insights
- Initialize before FastAPI app starts (lifespan event)
- Automatically instruments: `httpx`, `fastapi`, `openai`, `azure-core` via included OTel instrumentors
- Set `APPLICATIONINSIGHTS_CONNECTION_STRING` from environment
- Set `service.name`, `service.version`, `deployment.environment` resource attributes

**Auto-collected signals (out of the box)**

- Distributed traces for all inbound HTTP requests (FastAPI) and outbound calls (httpx, Azure SDKs, OpenAI SDK)
- W3C `traceparent` / `tracestate` propagation between frontend → BFF → Azure services
- Dependency tracking (Cosmos DB, AI Search, OpenAI, API Center)
- Exception telemetry with stack traces
- Live metrics stream

### 2. Custom OTel Metrics (`metrics.py`)

Define a custom `Meter` with the following instruments:

**Request/feature metrics**
| Metric Name | Type | Unit | Attributes | Description |
|-------------|------|------|------------|-------------|
| `apic.api_center.requests` | Histogram | `ms` | `operation`, `status_code` | API Center call latency |
| `apic.search.queries` | Histogram | `ms` | `query_type`, `result_count`, `status_code` | Search request latency and result volume |
| `apic.chat.messages` | Counter | `{message}` | `session_id`, `role` | Chat message count |
| `apic.chat.latency` | Histogram | `ms` | `streaming` | End-to-end chat response time |
| `apic.cache.lookups` | Counter | `{lookup}` | `hit` | Cache hit/miss ratio |
| `apic.auth.failures` | Counter | `{failure}` | `reason` | Authentication failure count |
| `apic.agent.invocations` | Counter | `{invocation}` | `agent_type`, `status` | Agent invocation count |

**Token usage metrics (see §3)**
| Metric Name | Type | Unit | Attributes | Description |
|-------------|------|------|------------|-------------|
| `apic.llm.tokens.estimated` | Histogram | `{token}` | `model`, `component` | Pre-call token estimate via tiktoken |
| `apic.llm.tokens.prompt` | Histogram | `{token}` | `model` | Actual prompt tokens (from OpenAI response) |
| `apic.llm.tokens.completion` | Histogram | `{token}` | `model` | Actual completion tokens (from response) |
| `apic.llm.tokens.total` | Histogram | `{token}` | `model` | Actual total tokens (prompt + completion) |
| `apic.llm.cost.estimated` | Histogram | `USD` | `model` | Estimated cost based on token pricing |

### 3. Token Metrics with tiktoken (`token_metrics.py`)

Use `tiktoken` for pre-call token estimation and the OpenAI response `usage` object for actual token counts:

**Pre-call estimation (tiktoken)**

- Before each OpenAI API call, use `tiktoken.encoding_for_model(model)` to count tokens in:
  - System prompt
  - Conversation history (sliding window)
  - RAG context documents
- Emit `apic.llm.tokens.estimated` histogram with `component` attribute (`system_prompt`, `history`, `rag_context`, `user_message`)
- Use estimates to enforce token budget and truncate context if needed (from task 017)

**Post-call actuals (OpenAI response)**

- Extract `usage.prompt_tokens`, `usage.completion_tokens`, `usage.total_tokens` from the OpenAI response
- Emit `apic.llm.tokens.prompt`, `apic.llm.tokens.completion`, `apic.llm.tokens.total` histograms
- Calculate estimated cost from token counts × per-token pricing (configurable per model)
- Emit `apic.llm.cost.estimated` histogram

**Drift tracking**

- Log a warning when estimated tokens differ from actual by >10% (helps calibrate prompts)

### 4. BFF Structured Logging + OTel Integration

- Integrate `structlog` (from task 006) with OpenTelemetry logging bridge
- All log records automatically include `trace_id` and `span_id` for correlation
- Azure Monitor distro exports logs to App Insights as trace records
- Log levels: `DEBUG` for detailed operation tracing, `INFO` for key events, `WARNING` for drift/anomalies, `ERROR` for failures
- Critical events to log: search queries, chat completions, auth events, token budget overruns

### 5. Frontend Telemetry

```
src/frontend/lib/
├── telemetry/
│   ├── app-insights-browser.ts  # Browser SDK initialization
│   ├── use-tracking.ts          # Custom hook for tracking
│   └── track-events.ts          # Typed event tracking functions
```

- Use `@microsoft/applicationinsights-web` browser SDK
- Configure with App Insights connection string from environment
- Enable W3C distributed tracing — the SDK automatically generates `traceparent` headers on XHR/fetch calls, creating end-to-end correlation with the BFF
- Auto-collect: page views, exceptions, AJAX/fetch dependencies
- Custom events:
  - `search_performed` — Query text, result count, duration
  - `api_viewed` — API ID, source (catalog, search, chat)
  - `chat_message_sent` — Message length, session ID
  - `filter_applied` — Filter type and value
  - `spec_downloaded` — API ID, format

### 6. End-to-End Distributed Tracing

- Frontend SDK generates `traceparent` header automatically on outbound requests
- BFF: Azure Monitor OTel distro auto-propagates W3C Trace Context (`traceparent` / `tracestate`) across all outbound calls (httpx → Azure SDKs, OpenAI)
- Full trace path: **Browser → BFF (FastAPI) → Cosmos DB / AI Search / OpenAI / API Center**
- All spans visible in App Insights **Transaction Search** and **Application Map**
- Custom span attributes added where useful (e.g., `chat.session_id`, `search.query_type`)

### 7. Error Tracking

- Frontend: Catch unhandled errors and promise rejections (auto-captured by browser SDK)
- BFF: OTel distro auto-captures unhandled exceptions; custom exception handler enriches spans with context (user ID, request path)
- Alert on error rate spikes (configure in App Insights alert rules)

### 8. App Insights Dashboards & Alerts

Define an App Insights workbook or dashboard covering:

- **Request metrics**: Rate, latency (p50/p95/p99), error rate (BFF)
- **Token usage**: Estimated vs actual tokens, cost trends, per-model breakdown
- **Search metrics**: Query volume, latency, result counts, zero-result rate
- **Chat metrics**: Messages per session, response latency, streaming vs sync
- **Dependency health**: API Center, AI Search, OpenAI, Cosmos DB — latency and failure rate
- **Frontend**: Page load times, JS errors, AJAX failure rate

**Alerts**:

- Error rate > 5% over 5 min window
- P95 latency > 2s for BFF requests
- Token cost exceeding daily budget threshold
- Dependency failure rate > 1%

### 9. Availability Tests

- Configure availability ping tests for:
  - Frontend health endpoint
  - BFF `/health` endpoint
  - BFF `/health/ready` endpoint

## Testing & Acceptance Criteria

- [ ] BFF uses `azure-monitor-opentelemetry` distro and sends traces, metrics, and logs to App Insights
- [ ] W3C Trace Context propagates end-to-end: frontend → BFF → Azure services
- [ ] Custom OTel metrics are emitted for search, chat, cache, auth, and agent invocations
- [ ] Token estimation via tiktoken emits `apic.llm.tokens.estimated` metrics
- [ ] Actual token usage from OpenAI responses emits `apic.llm.tokens.prompt/completion/total` metrics
- [ ] Estimated cost metric (`apic.llm.cost.estimated`) is emitted per request
- [ ] structlog logs include `trace_id` and `span_id` for correlation
- [ ] Frontend sends page views, custom events, and exceptions to App Insights
- [ ] Frontend XHR/fetch calls include `traceparent` header
- [ ] Unhandled errors in both frontend and BFF are captured with full context
- [ ] App Insights dashboard shows key operational and token usage metrics
- [ ] Availability tests run and report correctly
- [ ] Telemetry initialization doesn't impact application startup time
- [ ] Unit tests verify custom metric recording (with mocked OTel meter)

## Implementation Notes

<!--
  This section is a living record updated by the implementing agent.
  Update status, log decisions, and record validation results as work progresses.
  When complete, change the Status at the top of this document to ✅ Complete.
-->

### Status History

| Date       | Status         | Author   | Notes                                                                                                                                                                                       |
| ---------- | -------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| —          | 🔲 Not Started | —        | Task created                                                                                                                                                                                |
| 2026-04-19 | ✅ Complete    | @copilot | BFF `telemetry/` module (OTel setup, custom metrics, token metrics, middleware), indexer telemetry, frontend App Insights SDK + typed tracking helpers, 43 new tests (32 BFF + 11 frontend) |

### Technical Decisions

- `azure-monitor-opentelemetry` is imported inside `try/except` blocks so the package is optional and tests run without it installed
- `tiktoken` fallback to `chars / 4` estimation when the model encoding is not found, to avoid crashing on unsupported model names
- OTel `_meter` singleton is reset per-test by setting `metrics._meter = None`, keeping tests isolated
- Frontend App Insights SDK wrapped in a singleton factory (`getAppInsights()`) that is a no-op when `NEXT_PUBLIC_APPLICATIONINSIGHTS_CONNECTION_STRING` is unset
- `TelemetryProvider` is a `"use client"` component rendered inside `<Suspense>` in the root layout (required because it uses `useSearchParams()`)
- Indexer instrumented with a root span `indexer.full_reindex` to wrap the entire job invocation
- OTel trace context (`trace_id`, `span_id`) injected into both BFF structlog and indexer structlog via a custom processor

### Deviations from Plan

- Indexer container instrumented in addition to the BFF (per agent instructions) — not in the original spec but consistent with the architecture goal
- Frontend `TelemetryProvider` is a dedicated client component rather than inline in `layout.tsx` to keep the server component clean

### Validation Results

- **BFF tests**: 522 passed (490 pre-existing + 32 new telemetry tests) — `uv run pytest` ✅
- **BFF lint**: `ruff check` + `ruff format --check` all pass ✅
- **Indexer tests**: 83 passed — `uv run pytest` ✅
- **Indexer lint**: `ruff check` + `ruff format --check` all pass ✅
- **Frontend tests**: 198 passed (187 pre-existing + 11 new telemetry tests); 14 pre-existing failures (unrelated `@apic-vibe-portal/shared` module resolution in Jest) ✅
- **Frontend lint**: `eslint .` passes ✅

## Coding Agent Prompt

```text
**Task**: Implement plan step 019 — End-to-End OpenTelemetry Observability.

Read the full task specification at `docs/project/plan/019-observability-app-insights.md`.

Reference the architecture at `docs/project/apic_architecture.md` (Observability: App Insights) and `docs/project/plan/002-sprint-zero-azure-infra-bicep.md` for the App Insights resource.

In the BFF (`src/bff/`), integrate the `azure-monitor-opentelemetry` distro via `configure_azure_monitor()` for automatic trace/metric/log export to App Insights. Define custom OTel metrics using the OpenTelemetry Meter API for search queries, chat messages, cache lookups, auth failures, and agent invocations. Implement token usage metrics using `tiktoken` for pre-call estimation and OpenAI response `usage` for actuals — emit histograms for estimated tokens, actual prompt/completion/total tokens, and estimated cost. Integrate structlog with the OTel logging bridge so all logs carry trace_id/span_id. In the frontend, integrate `@microsoft/applicationinsights-web` with W3C distributed tracing, page views, custom events, and error tracking.

Write tests verifying custom metrics are emitted correctly (mocked OTel meter). Verify all tests pass with `uv run pytest`.

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/019-observability-app-insights.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
