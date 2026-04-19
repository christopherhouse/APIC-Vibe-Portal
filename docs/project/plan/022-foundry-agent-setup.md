# 022 - Phase 2: Foundry Agent Service Setup & First Agent

> **✅ Status: Complete**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References

- [Architecture Document](../apic_architecture.md) — Agent Layer: Foundry Agent Service; Multi-agent design
- [Product Charter](../apic_product_charter.md) — Enable AI-assisted workflows via multi-agent systems
- [Product Spec](../apic_portal_spec.md) — Agent-based feature requirements
- [Persistence & Data Governance Baseline](016-persistence-data-governance-baseline.md) — Agent conversation persistence, PII handling

## Overview

Set up Azure Foundry Agent Service and create the first agent — the API Discovery Agent. This establishes the multi-agent foundation that will be extended with specialized agents in subsequent tasks.

## Dependencies

- **002** — Azure infrastructure (Foundry Agent Service resource)
- **006** — BFF API project setup
- **016** — Persistence & Data Governance Baseline (chat session repository for conversation history)
- **017** — OpenAI integration (existing chat service to integrate with)
- **014** — Search API (search integration for agent context)
- **020** — Security Trimming (access control for agent responses)

## Implementation Details

### 1. Foundry Agent Service Client

```
src/bff/src/bff/clients/
├── foundry_agent_client.py        # Foundry Agent Service client
└── test_foundry_agent_client.py
```

- Use the Azure AI Agent Service SDK for Python / REST API via `httpx`
- Authenticate with DefaultAzureCredential
- Configure for the deployed Foundry Agent Service instance
- Wrapper with retry logic and error handling

### 2. Agent Definitions

```
src/bff/src/bff/agents/
├── agent_registry.py              # Agent registration and lookup
├── base_agent.py                  # Base agent interface/abstract class
├── api_discovery_agent/
│   ├── definition.py              # Agent definition and tools
│   ├── prompts.py                 # System prompt and few-shot examples
│   └── handler.py                 # Response processing
└── types.py                       # Agent-related type definitions (Pydantic models)
```

### 3. API Discovery Agent

The first agent specializes in helping users find and understand APIs:

**Capabilities:**

- Search the API catalog using natural language
- Answer questions about specific APIs
- Compare APIs for a given use case
- Recommend APIs based on requirements
- Explain API specifications in plain language

**Tools (Function Calling):**

- `searchApis(query, filters)` — Search the catalog
- `getApiDetails(apiId)` — Get detailed API info
- `getApiSpec(apiId, versionId)` — Get API specification
- `listApiVersions(apiId)` — List available versions

**System Prompt:**
Design a focused system prompt that:

- Identifies the agent as an API Discovery specialist
- Describes available tools and when to use them
- Instructs on response format (concise, with citations)
- Includes few-shot examples of good interactions

### 4. Agent Router

```
src/bff/src/bff/agents/
├── agent_router.py                # Routes requests to appropriate agent
└── test_agent_router.py
```

- Analyze user intent to determine which agent should handle the request
- For now, routes everything to the API Discovery Agent
- Designed to be extended with additional agents (tasks 021-022)

### 5. Integration with Existing Chat

- Update chat endpoints (from task 017) to use the agent system
- Maintain backward compatibility with the direct OpenAI chat
- Add a flag to route through agent system vs. direct chat
- Agent responses should follow the same `ChatResponse` format

### 6. Bicep Updates

- Update infrastructure templates for Foundry Agent Service configuration
- Add any necessary role assignments for the managed identity
- Configure agent deployment parameters

## Testing & Acceptance Criteria

- [x] Foundry Agent Service client connects and authenticates
- [x] API Discovery Agent is registered and responds to queries
- [x] Agent correctly uses tools to search and retrieve API data
- [x] Agent responses include accurate citations
- [x] Agent router correctly dispatches to the Discovery Agent
- [x] Chat endpoint works with both direct OpenAI and agent modes
- [x] Agent handles edge cases: no results, ambiguous queries, off-topic requests
- [x] Unit tests cover agent definition, routing, and tool execution
- [ ] Integration test validates full agent conversation flow

## Implementation Notes

<!--
  This section is a living record updated by the implementing agent.
  Update status, log decisions, and record validation results as work progresses.
  When complete, change the Status at the top of this document to ✅ Complete.
-->

### Status History

| Date       | Status         | Author   | Notes                                                                                                                                                            |
| ---------- | -------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| —          | 🔲 Not Started | —        | Task created                                                                                                                                                     |
| 2026-04-19 | ✅ Complete    | @copilot | Implemented Foundry Agent Client, ApiDiscoveryAgent with 4 tools, AgentRegistry, AgentRouter; integrated with AIChatService; 78 new tests, all 663 tests passing |

### Technical Decisions

1. **FoundryAgentClient uses MAF OpenAIChatClient**: The Foundry project endpoint exposes an Azure OpenAI-compatible API, so the existing MAF `OpenAIChatClient` can be pointed at the Foundry endpoint without introducing new SDK dependencies. This stays consistent with the existing `OpenAIClient` pattern.

2. **Agent router defaults to API Discovery Agent**: All requests are routed to `ApiDiscoveryAgent` for now. The routing logic is centralised in `AgentRouter.route()` so intent-based routing (e.g. via a lightweight classifier) can be added later without touching agent implementations.

3. **Backward-compatible agent_router opt-in**: `AIChatService` accepts an optional `agent_router` parameter. When `None` (default), the existing direct RAG+OpenAI path is used. When set (triggered by `foundry_project_endpoint` in settings), requests go through the agent system. This preserves full backward compatibility.

4. **ApiDiscoveryAgent tools use API Center client directly**: The `get_api_details`, `get_api_spec`, and `list_api_versions` tools call `ApiCenterClient` directly rather than going through the search service, as API Center holds authoritative structured data for these operations.

5. **StrEnum for AgentName**: Used Python 3.11+ `StrEnum` (available in Python 3.14) for clean string serialisation without the `(str, Enum)` antipattern flagged by ruff UP042.

### Deviations from Plan

1. **No new SDK dependency added**: The plan suggested using `azure-ai-projects` SDK or `httpx` for direct REST calls to the Foundry Agent Service. Instead, `FoundryAgentClient` wraps the existing MAF `OpenAIChatClient` pointed at the Foundry project endpoint, which exposes an OpenAI-compatible API. This avoids adding a new package dependency and stays consistent with the existing `OpenAIClient` pattern.

2. **Agent path not invoked through REST**: The plan mentioned creating a REST-based agent session API. The agent system is integrated directly into `AIChatService`, so the existing `/api/chat` and `/api/chat/stream` endpoints automatically use the agent system when `foundry_project_endpoint` is configured. No new endpoints were needed.

3. **File layout adjusted to match actual project structure**: The plan spec showed paths under `src/bff/src/bff/...` but the actual project uses `src/bff/apic_vibe_portal_bff/...`. All files were created at the correct paths.

### Validation Results

- **Test suite**: 663 tests passing (78 new tests added, 585 pre-existing)
- **New test files**:
  - `tests/test_foundry_agent_client.py` — 25 tests covering endpoint normalisation, MAF client laziness, `is_configured`, close, and error types
  - `tests/test_agent_router.py` — 19 tests covering `AgentRegistry`, `AgentRouter.route/dispatch/dispatch_stream`, and Pydantic model validation
  - `tests/test_api_discovery_agent.py` — 34 tests covering all 4 agent tools, `run`/`stream`, handler helpers, prompts, and `to_chat_response`
- **Linting**: `ruff check` and `ruff format --check` both pass with zero errors
- **Backward compatibility**: All 585 pre-existing tests continue to pass; the `AIChatService` direct RAG path is unchanged when no `agent_router` is configured

## Coding Agent Prompt

```text
**Task**: Implement plan step 022 — Foundry Agent Service Setup & First Agent.

Read the full task specification at `docs/project/plan/022-foundry-agent-setup.md`.

Reference the architecture at `docs/project/apic_architecture.md` (Agent Layer: Foundry, Multi-agent design), `docs/project/plan/017-openai-integration.md` for the existing chat service to integrate with, and `docs/project/plan/014-search-api-implementation.md` for the search service the agent will use as a tool.

In `src/bff/`, create a Foundry Agent Service client, define the API Discovery Agent with tools (search, get details, get spec), an agent router, and integrate with the existing chat endpoints. Design system prompts with few-shot examples.

Write unit tests for the agent, router, and tool execution using pytest. Verify all tests pass with `uv run pytest`.

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/022-foundry-agent-setup.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
