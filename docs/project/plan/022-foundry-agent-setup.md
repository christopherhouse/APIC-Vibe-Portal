# 022 - Phase 2: Foundry Agent Service Setup & First Agent

> **🔲 Status: Not Started**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References
- [Architecture Document](../apic_architecture.md) — Agent Layer: Foundry Agent Service; Multi-agent design
- [Product Charter](../apic_product_charter.md) — Enable AI-assisted workflows via multi-agent systems
- [Product Spec](../apic_portal_spec.md) — Agent-based feature requirements

## Overview
Set up Azure Foundry Agent Service and create the first agent — the API Discovery Agent. This establishes the multi-agent foundation that will be extended with specialized agents in subsequent tasks.

## Dependencies
- **002** — Azure infrastructure (Foundry Agent Service resource)
- **006** — BFF API project setup
- **017** — OpenAI integration (existing chat service to integrate with)

## Implementation Details

### 1. Foundry Agent Service Client
```
src/bff/src/clients/
├── foundry-agent-client.ts        # Foundry Agent Service client
└── foundry-agent-client.test.ts
```

- Use the Azure AI Agent Service SDK / REST API
- Authenticate with DefaultAzureCredential
- Configure for the deployed Foundry Agent Service instance
- Wrapper with retry logic and error handling

### 2. Agent Definitions
```
src/bff/src/agents/
├── agent-registry.ts              # Agent registration and lookup
├── base-agent.ts                  # Base agent interface/abstract class
├── api-discovery-agent/
│   ├── definition.ts              # Agent definition and tools
│   ├── prompts.ts                 # System prompt and few-shot examples
│   └── handler.ts                 # Response processing
└── types.ts                       # Agent-related type definitions
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
src/bff/src/agents/
├── agent-router.ts                # Routes requests to appropriate agent
└── agent-router.test.ts
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
- [ ] Foundry Agent Service client connects and authenticates
- [ ] API Discovery Agent is registered and responds to queries
- [ ] Agent correctly uses tools to search and retrieve API data
- [ ] Agent responses include accurate citations
- [ ] Agent router correctly dispatches to the Discovery Agent
- [ ] Chat endpoint works with both direct OpenAI and agent modes
- [ ] Agent handles edge cases: no results, ambiguous queries, off-topic requests
- [ ] Unit tests cover agent definition, routing, and tool execution
- [ ] Integration test validates full agent conversation flow

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

```text
**Task**: Implement plan step 022 — Foundry Agent Service Setup & First Agent.

Read the full task specification at `docs/project/plan/022-foundry-agent-setup.md`.

Reference the architecture at `docs/project/apic_architecture.md` (Agent Layer: Foundry, Multi-agent design), `docs/project/plan/014-openai-integration.md` for the existing chat service to integrate with, and `docs/project/plan/012-search-api-implementation.md` for the search service the agent will use as a tool.

In `src/bff/`, create a Foundry Agent Service client, define the API Discovery Agent with tools (search, get details, get spec), an agent router, and integrate with the existing chat endpoints. Design system prompts with few-shot examples.

Write unit tests for the agent, router, and tool execution. Verify the build succeeds and all tests pass.

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/022-foundry-agent-setup.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
