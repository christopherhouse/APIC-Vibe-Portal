# 014 - Phase 1 MVP: Azure OpenAI Service Integration (BFF)

> **🔲 Status: Not Started**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References
- [Architecture Document](../apic_architecture.md) — Azure OpenAI for AI features
- [Product Charter](../apic_product_charter.md) — Enable AI-assisted workflows
- [Product Spec](../apic_portal_spec.md) — AI-powered features requirements

## Overview
Integrate Azure OpenAI into the BFF to power AI-assisted API discovery through a conversational chat interface. This enables developers to ask natural language questions about APIs and receive contextual, grounded answers.

## Dependencies
- **002** — Azure infrastructure (OpenAI resource deployed)
- **005** — BFF API project setup
- **006** — Shared types package (chat DTOs)
- **011** — AI Search index (used for RAG retrieval)

## Implementation Details

### 1. OpenAI Client
```
src/bff/src/clients/
├── openai-client.ts           # Azure OpenAI client wrapper
└── openai-client.test.ts
```

- Use `@azure/openai` SDK or `openai` npm package with Azure configuration
- Authenticate with DefaultAzureCredential
- Configure for the deployed GPT model (e.g., gpt-4o)
- Support streaming responses

### 2. RAG (Retrieval-Augmented Generation) Service
```
src/bff/src/services/
├── ai-chat.service.ts          # RAG-powered chat service
└── ai-chat.service.test.ts
```

Implement a RAG pipeline:
1. **Receive** user question
2. **Retrieve** relevant API documents from AI Search (hybrid search from task 012)
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
  sessionId?: string;         // For conversation continuity
  includeContext?: boolean;    // Include RAG context in response
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
- Use Server-Sent Events (SSE) for streaming responses
- Stream tokens as they are generated
- Include a final event with citations and metadata
- Frontend can show incremental text rendering

### 7. Token Management & Safety
- Count tokens in prompt + context to stay within model limits
- Truncate context if it exceeds token budget
- Implement content filtering (Azure OpenAI built-in + additional checks)
- Rate limiting per session (e.g., 30 messages per minute)

## Testing & Acceptance Criteria
- [ ] `POST /api/chat` returns an AI-generated response grounded in API catalog data
- [ ] Responses include citations to specific APIs
- [ ] Conversation history is maintained within a session
- [ ] `POST /api/chat/stream` returns streaming SSE response
- [ ] RAG pipeline retrieves relevant APIs from AI Search
- [ ] System prompt keeps responses focused on API domain
- [ ] Token limits are enforced; long contexts are truncated appropriately
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
| Date | Status | Author | Notes |
|------|--------|--------|-------|
| — | 🔲 Not Started | — | Task created |

### Technical Decisions
_No technical decisions recorded yet._

### Deviations from Plan
_No deviations from the original plan._

### Validation Results
_No validation results yet._


## Coding Agent Prompt

> **Task**: Implement plan step 014 — Azure OpenAI Service Integration.
>
> Read the full task specification at `docs/project/plan/014-openai-integration.md`.
>
> Reference the architecture at `docs/project/apic_architecture.md` (Azure OpenAI for AI features), `docs/project/plan/012-search-api-implementation.md` for the search service used in RAG retrieval, and `docs/project/plan/006-shared-types-package.md` for chat DTOs.
>
> In `src/bff/`, create an Azure OpenAI client wrapper, a RAG-powered chat service (retrieve from AI Search → augment prompt → generate with OpenAI), chat endpoints with both synchronous and SSE streaming responses, conversation session management, and token/rate limiting. Design the system prompt for an API discovery assistant.
>
> Write unit tests with mocked OpenAI and AI Search responses. Verify the build succeeds and all tests pass.
>
> **Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/014-openai-integration.md`):
> 1. Change the status banner at the top to `> **✅ Status: Complete**`
> 2. Add a row to the Status History table with the completion date and a summary
> 3. Record any technical decisions made under "Technical Decisions"
> 4. Note any deviations from the plan under "Deviations from Plan"
> 5. Record test/validation results under "Validation Results"
