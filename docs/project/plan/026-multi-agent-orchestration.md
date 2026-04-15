# 026 - Phase 2: Multi-Agent Orchestration & Agent Management

> **🔲 Status: Not Started**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References

- [Architecture Document](../apic_architecture.md) — Multi-agent design; Agent Layer: Foundry
- [Product Charter](../apic_product_charter.md) — Enable AI-assisted workflows through multiple specialized agents
- [Product Spec](../apic_portal_spec.md) — Advanced AI feature requirements

## Overview

Enhance the multi-agent architecture with sophisticated orchestration, agent hand-off, and an admin interface for managing agent configurations. This enables seamless multi-turn conversations where multiple agents collaborate to answer complex queries.

## Dependencies

- **022** — Foundry Agent setup (base agent framework)
- **023** — Governance Agent (second agent in the system)
- **008** — Entra ID authentication (admin-only management features)

## Implementation Details

### 1. Agent Orchestrator

```
src/bff/src/bff/agents/
├── orchestrator.py                 # Multi-agent orchestrator
├── test_orchestrator.py
├── intent_classifier.py           # Intent classification for routing
└── test_intent_classifier.py
```

**Orchestration Capabilities:**

- Classify user intent to select the best agent
- Support agent hand-off within a conversation
- Allow agents to delegate to other agents
- Maintain conversation context across agent switches
- Fallback handling when no agent is confident

### 2. Intent Classification

- Use a lightweight classifier (could be rule-based + LLM fallback)
- Intent categories:
  - `discovery` → API Discovery Agent
  - `governance` → Governance Agent
  - `comparison` → Discovery Agent (with compare tool)
  - `general` → Default fallback (Discovery Agent)
- Confidence threshold: above 0.7 route directly, below 0.7 ask for clarification

### 3. Agent Hand-off Protocol

- When an agent determines another agent would better serve the user:
  1. Current agent generates a summary of the conversation so far
  2. Orchestrator routes to the new agent
  3. New agent receives conversation summary and continues
  4. User sees a subtle notification: "I'm connecting you with our Governance specialist..."
- Hand-off state is preserved in the session

### 4. Conversation Context Management

```
src/bff/src/bff/agents/
├── context_manager.py             # Cross-agent context management
└── test_context_manager.py
```

- Maintain a shared context across agent switches
- Context includes: conversation history, referenced APIs, active filters
- Context window management: summarize older turns to stay within token limits
- Session-level context with configurable max size

### 5. Agent Management API (Admin)

```
src/bff/src/bff/routers/
├── admin/
│   ├── agent_management.py
│   └── test_agent_management.py
```

Endpoints (require `Portal.Admin` role):
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/admin/agents` | List all registered agents |
| `GET` | `/api/admin/agents/:agentId` | Get agent details |
| `PUT` | `/api/admin/agents/:agentId/config` | Update agent configuration |
| `GET` | `/api/admin/agents/:agentId/stats` | Agent usage statistics |
| `POST` | `/api/admin/agents/:agentId/test` | Test agent with sample query |

### 6. Agent Admin UI (Frontend)

```
app/admin/agents/
├── page.tsx                # Agent management dashboard
└── [agentId]/
    └── page.tsx            # Agent detail/configuration
```

- List all agents with status indicators
- View agent configuration and system prompt
- View usage statistics (queries handled, avg response time)
- Test agent with sample queries
- Admin-only access (gated by role)

## Testing & Acceptance Criteria

- [ ] Intent classifier correctly routes queries to appropriate agents
- [ ] Agent hand-off preserves conversation context
- [ ] User sees smooth transition during agent hand-off
- [ ] Orchestrator handles low-confidence classifications gracefully
- [ ] Conversation context is maintained across agent switches
- [ ] Admin API correctly manages agent configurations
- [ ] Admin UI displays agent list and stats
- [ ] Admin-only routes reject non-admin users (403)
- [ ] Unit tests cover orchestrator, classifier, and context management
- [ ] Integration test validates multi-agent conversation flow

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
**Task**: Implement plan step 026 — Multi-Agent Orchestration & Agent Management.

Read the full task specification at `docs/project/plan/026-multi-agent-orchestration.md`.

Reference `docs/project/plan/022-foundry-agent-setup.md` for the base agent framework and router, `docs/project/plan/023-governance-agent.md` for the second agent, and `docs/project/plan/008-entra-id-authentication.md` for admin role gating.

Implement a multi-agent orchestrator with intent classification, agent hand-off protocol with context preservation, cross-agent conversation context management, admin API endpoints for agent management, and an admin UI for viewing/configuring agents.

Write unit tests for the orchestrator, intent classifier, context manager, and admin endpoints using pytest (BFF) and Jest (frontend). Verify all tests pass.

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/026-multi-agent-orchestration.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
