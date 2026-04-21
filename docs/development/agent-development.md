# Agent Development Guide

This guide explains how to create new AI agents for the APIC Vibe Portal AI using **Azure Foundry Agent Service**.

## Agent Architecture Overview

The portal uses a **multi-agent orchestration** pattern:

```
User Request
    │
    ▼
Orchestrator Agent
    ├── dispatches to specialist agents
    ├── aggregates responses
    └── streams final response to user

Specialist Agents:
├── Search Agent       — API discovery via AI Search
├── Governance Agent   — Compliance analysis
├── Comparison Agent   — Side-by-side API comparison
└── Catalog Agent      — API detail retrieval
```

Agents are defined in `src/bff/agents/` and registered with Foundry Agent Service.

## Creating a New Agent

### Step 1: Define the Agent Schema

Create a new Python module in `src/bff/agents/`:

```python
# src/bff/agents/my_new_agent.py

from pydantic import BaseModel
from typing import Any


class MyNewAgentInput(BaseModel):
    """Input schema for MyNewAgent."""
    query: str
    context: dict[str, Any] | None = None


class MyNewAgentOutput(BaseModel):
    """Output schema for MyNewAgent."""
    result: str
    confidence: float
    sources: list[str] = []
```

### Step 2: Implement the Agent Logic

```python
# src/bff/agents/my_new_agent.py (continued)

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential


async def run_my_new_agent(
    client: AIProjectClient,
    agent_id: str,
    input_data: MyNewAgentInput,
) -> MyNewAgentOutput:
    """Run the agent and return structured output."""
    thread = await client.agents.create_thread()

    await client.agents.create_message(
        thread_id=thread.id,
        role="user",
        content=input_data.query,
    )

    run = await client.agents.create_and_process_run(
        thread_id=thread.id,
        agent_id=agent_id,
    )

    messages = await client.agents.list_messages(thread_id=thread.id)
    response_text = messages.data[0].content[0].text.value

    return MyNewAgentOutput(
        result=response_text,
        confidence=0.9,
        sources=[],
    )
```

### Step 3: Add a System Prompt

Create a system prompt file for your agent:

```
# src/bff/agents/prompts/my_new_agent_system.md

You are a specialist AI agent in the APIC Vibe Portal AI.

Your role is to [describe what the agent does].

When responding:
- Be concise and technical
- Reference specific API names when known
- Format code examples with appropriate language tags
- If you cannot answer, explain why

Available tools:
- [list any tools/functions the agent can call]
```

### Step 4: Register the Agent

Register the new agent in `src/bff/agents/registry.py`:

```python
AGENT_REGISTRY = {
    "my-new-agent": {
        "name": "My New Agent",
        "description": "Handles [X] queries",
        "model": "gpt-4o",
        "system_prompt_path": "agents/prompts/my_new_agent_system.md",
    },
    # ... existing agents
}
```

### Step 5: Create the Agent in Foundry Service

Use the BFF admin API to create the agent in Foundry Agent Service:

```bash
curl -X POST https://<bff-url>/api/admin/agents \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "agentId": "my-new-agent",
    "forceRecreate": false
  }'
```

Alternatively, run the agent setup script:

```bash
cd src/bff
uv run python scripts/setup_agents.py --agent my-new-agent
```

### Step 6: Integrate with the Orchestrator

Update the orchestrator to dispatch to your new agent when appropriate:

```python
# src/bff/agents/orchestrator.py

async def route_to_specialist(query: str, context: dict) -> str:
    intent = await classify_intent(query)

    if intent == "my_new_intent":
        return await run_my_new_agent(client, AGENT_IDS["my-new-agent"], ...)

    # ... existing routing
```

### Step 7: Write Tests

Add tests in `src/bff/tests/test_my_new_agent.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch
from agents.my_new_agent import run_my_new_agent, MyNewAgentInput


@pytest.mark.asyncio
async def test_my_new_agent_returns_result():
    mock_client = AsyncMock()
    # Set up mock responses...

    result = await run_my_new_agent(
        mock_client,
        "agent-id",
        MyNewAgentInput(query="test query")
    )

    assert result.result != ""
    assert 0 <= result.confidence <= 1.0
```

## Agent Naming Conventions

| Component     | Convention               | Example                      |
| ------------- | ------------------------ | ---------------------------- |
| Python module | `snake_case_agent.py`    | `governance_agent.py`        |
| Agent ID      | kebab-case               | `governance-agent`           |
| Input class   | `<Name>AgentInput`       | `GovernanceAgentInput`       |
| Output class  | `<Name>AgentOutput`      | `GovernanceAgentOutput`      |
| System prompt | `<name>_agent_system.md` | `governance_agent_system.md` |

## System Prompt Guidelines

Good system prompts:

- Define the agent's role clearly in the first sentence
- Specify response format (prose, JSON, markdown)
- List what the agent should and should not do
- Describe how to handle uncertainty
- Are concise — avoid long preambles

Bad system prompts:

- Are vague about the agent's role
- Don't specify output format
- Are excessively long (> 1000 tokens)

## Testing Agents

Always test agents in a **staging environment** before deploying to production:

1. Create the agent with `-staging` suffix in staging: `my-new-agent-staging`
2. Test via the admin agent management page (`/admin/agents`)
3. Use the **Test Agent** dialog to send sample queries
4. Review the output quality and latency
5. When satisfied, create the production version

## Related Documentation

- **[Architecture Deep Dive](architecture-deep-dive.md)**
- **[Testing Guide](testing-guide.md)**
- **[Local Development](local-development.md)**
