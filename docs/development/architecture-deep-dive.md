# Architecture Deep Dive

This document provides a detailed technical overview of the APIC Vibe Portal AI architecture, building on the high-level [Architecture Document](../apic_architecture.md).

## System Components

```
┌──────────────────────────────────────────────────────────────┐
│                         Browser                              │
│  Next.js 16 App Router (SSR + Client Components)            │
│  Material UI · React 19 · TypeScript 6.0                     │
└─────────────────────┬────────────────────────────────────────┘
                      │ HTTP/HTTPS (Next.js API routes → BFF)
                      ▼
┌──────────────────────────────────────────────────────────────┐
│              Backend-for-Frontend (BFF)                      │
│  Python 3.14 · FastAPI · UV                                  │
│  Azure SDK for Python                                        │
└──────┬──────┬──────┬──────┬──────┬───────────────────────────┘
       │      │      │      │      │
  APIC │ Search│  OAI │ FAS  │Cosmos│
       ▼      ▼      ▼      ▼      ▼
  API      AI      Azure  Foundry  Cosmos
  Center  Search  OpenAI  Agents   DB
```

## Frontend Architecture

### Next.js App Router

The frontend uses the Next.js 16 **App Router** with:

- **Server Components** (default): Pages and layouts that render on the server
- **Client Components** (`"use client"`): Interactive components (chat, catalog filters, search)
- **Route groups** for organizational structure
- **Streaming** for real-time chat responses

### Directory Structure

```
src/frontend/app/
├── layout.tsx              # Root layout (App Shell)
├── page.tsx                # Root redirect → /catalog
├── catalog/
│   ├── page.tsx            # Catalog listing
│   └── [apiId]/
│       └── page.tsx        # API detail
├── search/
│   └── page.tsx            # Search results
├── chat/
│   └── page.tsx            # AI Chat
├── governance/
│   └── page.tsx            # Governance dashboard
├── compare/
│   └── page.tsx            # API comparison
└── admin/
    ├── analytics/
    │   └── page.tsx        # Analytics dashboard
    └── agents/
        └── page.tsx        # Agent management
```

### State Management

The portal uses React's built-in state management:

- **URL state** (via `useSearchParams`) for filterable/shareable pages
- **React hooks** (`useState`, `useReducer`, `useEffect`) for local component state
- **React Context** for cross-cutting state (auth, theme)

### Authentication Flow

1. `MsalProvider` wraps the app in the root layout
2. `useAuth` hook (in `lib/auth/`) reads the current user from MSAL or `window.__PLAYWRIGHT_USER__` (for E2E tests)
3. Protected routes check `useAuth().user` — if null, they show a sign-in prompt
4. RBAC checks compare `user.roles` to required roles using `hasRole()` helper

## BFF Architecture

### FastAPI Routers

The BFF is organized into FastAPI routers:

| Router       | Base path         | Responsibility                               |
| ------------ | ----------------- | -------------------------------------------- |
| `catalog`    | `/api/catalog`    | Proxy to Azure API Center                    |
| `search`     | `/api/search`     | Azure AI Search + semantic re-ranking        |
| `chat`       | `/api/chat`       | OpenAI streaming + Foundry Agent dispatch    |
| `governance` | `/api/governance` | Governance Agent results + compliance checks |
| `compare`    | `/api/compare`    | Multi-API comparison aggregation             |
| `analytics`  | `/api/analytics`  | Cosmos DB analytics queries                  |
| `admin`      | `/api/admin`      | Admin-only agent management                  |
| `health`     | `/health`         | Health check (no auth required)              |

### Authentication Middleware

Every request (except `/health`) passes through JWT validation middleware:

1. Extract `Authorization: Bearer <token>` header
2. Validate the JWT against the Entra ID tenant's JWKS endpoint
3. Extract claims (user ID, roles) and attach to `request.state.user`
4. Return `401 Unauthorized` if token is missing or invalid

### Security Trimming

The `security_trimming` module filters API results based on the authenticated user's roles:

- **`Portal.User`**: Sees only public-tagged APIs
- **`Portal.Maintainer`**: Sees all APIs
- **`Portal.Admin`**: Sees all APIs plus admin endpoints

## AI Layer Architecture

### Multi-Agent Orchestration

The AI layer uses **Foundry Agent Service** to coordinate multiple specialized agents:

```
User message
    │
    ▼
Orchestrator Agent
    ├── Search Agent       (semantic API discovery)
    ├── Governance Agent   (compliance analysis)
    ├── Comparison Agent   (side-by-side comparison)
    └── Catalog Agent      (API detail retrieval)
```

The Orchestrator determines which specialist agents to invoke based on the user's query intent.

### Chat Streaming

Chat responses are streamed using **Server-Sent Events (SSE)**:

1. BFF opens a streaming connection to Foundry Agent Service
2. Token chunks are forwarded to the frontend as SSE events
3. Frontend `EventSource` connection receives and renders tokens in real time

## Data Flow Examples

### API Catalog Browsing

```
Browser → GET /catalog → Next.js page → fetch /api/catalog
→ BFF catalog router → Azure API Center REST API
→ BFF: map response to shared types + apply security trimming
→ Browser: render API cards
```

### Semantic Search

```
Browser → POST /api/search { query, filters }
→ BFF search router
  → Azure AI Search: vector + keyword hybrid search
  → Re-rank results with semantic ranking
  → Apply security trimming
→ Browser: render ranked results
```

### AI Chat

```
Browser → POST /api/chat/stream { message, sessionId }
→ BFF chat router
  → Load/create session from Cosmos DB
  → Dispatch to Foundry Orchestrator Agent
    → Agent invokes Search/Governance/Catalog sub-agents as needed
    → Agent streams tokens back
  → Stream SSE events to browser
  → Save message to Cosmos DB
→ Browser: render streamed tokens
```

## Cross-Cutting Concerns

### Observability

All components instrument telemetry via Application Insights:

- **Frontend**: Azure Application Insights JavaScript SDK
- **BFF**: `opencensus-ext-azure` (or `azure-monitor-opentelemetry`) for distributed tracing

Custom events are tracked for:

- Search queries (query text, result count, duration)
- Chat interactions (session ID, message count)
- API detail views (API ID, tab)

### Error Handling

- **Frontend**: React Error Boundaries wrap each page; errors are caught and reported to App Insights
- **BFF**: FastAPI exception handlers return standardized error envelopes `{"error": {"code": "...", "message": "..."}}`

## Related Documentation

- **[Architecture Document](../apic_architecture.md)** — High-level overview
- **[Local Development](local-development.md)**
- **[Testing Guide](testing-guide.md)**
- **[Agent Development](agent-development.md)**
