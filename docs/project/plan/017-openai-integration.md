# 017 - Phase 1 MVP: Azure OpenAI Service Integration (BFF)

> **✅ Status: Complete**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References

- [Architecture Document](../apic_architecture.md) — Azure OpenAI for AI features
- [Product Charter](../apic_product_charter.md) — Enable AI-assisted workflows
- [Product Spec](../apic_portal_spec.md) — AI-powered features requirements
- [Persistence & Data Governance Baseline](016-persistence-data-governance-baseline.md) — Chat session storage strategy, PII handling, data retention policies

## Overview

Integrate Azure OpenAI into the BFF to power AI-assisted API discovery through a conversational chat interface. This enables developers to ask natural language questions about APIs and receive contextual, grounded answers.

## Dependencies

- **002** — Azure infrastructure (OpenAI resource deployed)
- **006** — BFF API project setup
- **007** — Shared types package (chat DTOs)
- **013** — AI Search index (used for RAG retrieval)
- **014** — Search API implementation (RAG retrieval pipeline)
- **016** — Persistence & Data Governance Baseline (chat session repository, schema versioning)

## Implementation Details

### 1. OpenAI Client

```
src/bff/src/bff/clients/
├── openai_client.py           # Azure OpenAI client wrapper
└── test_openai_client.py
```

- Use `openai` Python package with Azure configuration
- Authenticate with DefaultAzureCredential (via `azure-identity`)
- Configure for the deployed GPT model (e.g., gpt-4o)
- Support streaming responses

### 2. RAG (Retrieval-Augmented Generation) Service

```
src/bff/src/bff/services/
├── ai_chat_service.py          # RAG-powered chat service
└── test_ai_chat_service.py
```

Implement a RAG pipeline:

1. **Receive** user question
2. **Retrieve** relevant API documents from AI Search (hybrid search from task 014)
3. **Augment** the prompt with retrieved context
4. **Generate** response using Azure OpenAI with grounding data
5. **Return** response with citations to source APIs

### 3. System Prompt

Design a system prompt that:

- Identifies the assistant as an API discovery helper
- Instructs it to answer questions about APIs in the catalog
- Requires citations to specific APIs when referencing them
- Maintains professional, helpful tone
- Refuses to answer questions outside the API domain
- Encourages users to explore the catalog for more details

### 4. Chat Endpoints

```
POST /api/chat              # Send a message, get response
POST /api/chat/stream       # Send a message, get streaming response (SSE)
GET  /api/chat/history      # Get chat session history (in-memory or session-based)
DELETE /api/chat/history     # Clear chat history
```

Request body:

```typescript
interface ChatRequest {
  message: string;
  sessionId?: string; // For conversation continuity
  includeContext?: boolean; // Include RAG context in response
}
```

Response:

```typescript
interface ChatResponse {
  message: ChatMessage;
  citations: Citation[];
  sessionId: string;
}

interface Citation {
  apiId: string;
  apiName: string;
  title: string;
  relevanceScore: number;
  excerpt: string;
}
```

### 5. Conversation Management

- Maintain conversation history per session (in-memory for MVP)
- Include recent conversation turns in the prompt (sliding window: last 10 messages)
- Session expiry after 30 minutes of inactivity
- Each session has a unique ID returned to the frontend

### 6. Streaming Support

- Use Server-Sent Events (SSE) for streaming responses (via FastAPI `StreamingResponse`)
- Stream tokens as they are generated
- Include a final event with citations and metadata
- Frontend can show incremental text rendering

### 7. Token Management, Estimation & Usage Metrics

- Use `tiktoken` to estimate token counts before each OpenAI call:
  - Encode system prompt, conversation history, RAG context, and user message
  - Use `tiktoken.encoding_for_model(model)` for accurate model-specific counts
  - Emit `apic.llm.tokens.estimated` OTel histogram (from task 019) with `component` attribute
  - Enforce token budget: truncate RAG context or history if estimated tokens exceed model limit
- After each OpenAI response, extract `usage.prompt_tokens`, `usage.completion_tokens`, `usage.total_tokens`
  - Emit `apic.llm.tokens.prompt`, `apic.llm.tokens.completion`, `apic.llm.tokens.total` OTel histograms
  - Emit `apic.llm.cost.estimated` based on token counts × configured per-token pricing
  - Log warning if estimated tokens differ from actual by >10%
- Implement content filtering (Azure OpenAI built-in + additional checks)
- Rate limiting per session (e.g., 30 messages per minute)

## Testing & Acceptance Criteria

- [ ] `POST /api/chat` returns an AI-generated response grounded in API catalog data
- [ ] Responses include citations to specific APIs
- [ ] Conversation history is maintained within a session
- [ ] `POST /api/chat/stream` returns streaming SSE response
- [ ] RAG pipeline retrieves relevant APIs from AI Search
- [ ] System prompt keeps responses focused on API domain
- [ ] Token limits are enforced; long contexts are truncated based on tiktoken estimates
- [ ] `tiktoken` estimates are emitted as OTel metrics (`apic.llm.tokens.estimated`)
- [ ] Actual token usage from OpenAI responses is emitted as OTel metrics (`apic.llm.tokens.prompt/completion/total`)
- [ ] Estimated cost metric (`apic.llm.cost.estimated`) is emitted per chat request
- [ ] Rate limiting prevents abuse
- [ ] Unit tests cover chat service with mocked OpenAI and Search responses
- [ ] Session cleanup works after expiry

## Implementation Notes

<!--
  This section is a living record updated by the implementing agent.
  Update status, log decisions, and record validation results as work progresses.
  When complete, change the Status at the top of this document to ✅ Complete.
-->

### Status History

| Date       | Status         | Author | Notes                                                                                                                                                                                                                |
| ---------- | -------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| —          | 🔲 Not Started | —      | Task created                                                                                                                                                                                                         |
| 2026-04-18 | ✅ Complete     | Copilot | Implemented OpenAI client wrapper, RAG chat service, chat endpoints (sync + SSE streaming), session management, tiktoken token estimation, OTel metric stubs, rate limiting. 68 new tests, 481 total tests all green. |

### Technical Decisions

1. **Used `openai` Python SDK instead of Microsoft Agent Framework (MAF)**: MAF (`agent-framework` v1.0.1) was evaluated as the more modern approach and is GA, but has a Python 3.14 compatibility bug — `observability.py` tries to import `__version__` from the package `__init__.py` which is not defined, causing `ImportError` on any agent import. Since the BFF requires Python >= 3.14, MAF is currently unusable. The raw `openai` SDK works correctly on Python 3.14 and provides full control over the RAG pipeline. Migration to MAF should be revisited once the Python 3.14 compatibility issue is resolved upstream.
2. **In-memory session management for MVP**: Conversation sessions are stored in-memory using a thread-safe `SessionManager` class with sliding window history (last 10 turns) and 30-minute expiry. This is suitable for single-instance MVP deployments. For multi-replica scaling, sessions should be migrated to Redis or Cosmos DB.
3. **OTel metrics emitted via structured logging**: Token estimation and usage metrics (`apic.llm.tokens.*`, `apic.llm.cost.estimated`) are emitted as structured log entries. Task 019 will replace these with proper OpenTelemetry SDK histogram observations.
4. **Added `OPENAI_ENDPOINT` env var to BFF Container App**: The CD workflow (`deploy-app.yml`) now passes `OPENAI_ENDPOINT` to the BFF container in all three environments (dev, staging, prod), matching the existing pattern for the indexer container.
5. **Added `openai_chat_deployment` setting**: New configuration field defaulting to `gpt-4o` for the chat model deployment name, separate from the embedding deployment used by the indexer.

### Deviations from Plan

1. **Microsoft Agent Framework evaluated but not used**: The plan references Foundry Agent Service for multi-agent orchestration, but MAF has a Python 3.14 compatibility bug preventing its use. The `openai` SDK is used directly instead. This is a temporary deviation — MAF adoption should be revisited when the upstream bug is fixed.
2. **OTel metrics are stubs**: Metrics are emitted via structured logging rather than OTel SDK histograms, pending task 019 (observability setup).

### Validation Results

- **481 tests passing** (413 existing + 68 new), 0 failures
- **Ruff lint**: All checks passed
- **Ruff format**: All files formatted
- **Python compile check**: All files compile successfully
- New test files: `test_openai_client.py` (18 tests), `test_ai_chat_service.py` (33 tests), `test_chat_routes.py` (17 tests)
- Tests cover: client init/config, token acquisition, chat completion (sync/stream), error handling (rate limit, server error, generic), session management (create/get/expire/delete/cleanup), RAG context retrieval (with/without results, search failure), token estimation (tiktoken), metric emission (including drift warning), prompt construction, all route endpoints (POST /api/chat, POST /api/chat/stream, GET /api/chat/history, DELETE /api/chat/history), error handler formatting

## Coding Agent Prompt

```text
**Task**: Implement plan step 017 — Azure OpenAI Service Integration.

Read the full task specification at `docs/project/plan/017-openai-integration.md`.

Reference the architecture at `docs/project/apic_architecture.md` (Azure OpenAI for AI features), `docs/project/plan/014-search-api-implementation.md` for the search service used in RAG retrieval, and `docs/project/plan/007-shared-types-package.md` for chat DTOs.

In `src/bff/`, create an Azure OpenAI client wrapper (using the `openai` Python package with Azure config), a RAG-powered chat service (retrieve from AI Search → augment prompt → generate with OpenAI), FastAPI chat endpoints with both synchronous and SSE streaming responses, conversation session management, and token/rate limiting. Use `tiktoken` for pre-call token estimation and emit OTel metrics for both estimated and actual token usage (see task 019 for metric definitions). Design the system prompt for an API discovery assistant.

Write unit tests with mocked OpenAI and AI Search responses using pytest. Verify all tests pass with `uv run pytest`.

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/017-openai-integration.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
