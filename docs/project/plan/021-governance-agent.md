# 021 - Phase 2: Multi-Agent Architecture — Governance & Compliance Agent

> **🔲 Status: Not Started**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References
- [Architecture Document](../apic_architecture.md) — Multi-agent design; Agent Layer: Foundry
- [Product Charter](../apic_product_charter.md) — Provide governance visibility; metadata completeness as success metric
- [Product Spec](../apic_portal_spec.md) — Governance feature requirements

## Overview
Create a Governance & Compliance Agent that can assess API governance status, check compliance with organizational standards, and provide recommendations for improving API metadata quality. Extend the multi-agent router to dispatch governance-related queries to this agent.

## Dependencies
- **020** — Foundry Agent Service setup (agent framework, router)
- **007** — API Center data layer (governance metadata source)

## Implementation Details

### 1. Governance Agent Definition
```
src/bff/src/bff/agents/governance_agent/
├── definition.py              # Agent definition and tools
├── prompts.py                 # System prompt for governance focus
├── handler.py                 # Response processing
├── rules/
│   ├── governance_rules.py    # Governance rule definitions
│   └── compliance_checker.py  # Rule evaluation engine
└── tests/
    ├── test_governance_agent.py
    └── test_compliance_checker.py
```

### 2. Governance Rules Engine
Define configurable governance rules:
- **Metadata Completeness**: Description present, contacts defined, license specified, tags assigned
- **Versioning**: Follows semantic versioning, has active version
- **Specification Quality**: OpenAPI spec validates, endpoints documented, schemas defined
- **Lifecycle Compliance**: Deprecated APIs have sunset date, production APIs have SLA
- **Security**: Authentication documented, security schemes defined in spec
- **Documentation**: External docs linked, changelog maintained

Each rule has:
- ID, name, description
- Severity: `critical`, `warning`, `info`
- Evaluation function: `(api: ApiDefinition) => RuleResult`
- Remediation guidance

### 3. Agent Tools
- `checkApiCompliance(apiId)` — Run all governance rules against an API
- `getGovernanceScore(apiId)` — Calculate overall governance score (0-100)
- `listNonCompliantApis(rule?)` — Find APIs failing specific rules
- `getRemediationGuidance(apiId, ruleId)` — Get fix instructions
- `compareGovernanceScores(apiIds[])` — Compare scores across APIs

### 4. Agent System Prompt
Design prompt that:
- Identifies as a Governance & Compliance specialist
- Understands organizational API standards
- Can explain governance rules and their importance
- Provides actionable remediation guidance
- References specific governance rules by name

### 5. Agent Router Update
Update `agent_router.py` to:
- Detect governance-related intents (e.g., "Is this API compliant?", "Show governance issues")
- Route governance queries to the Governance Agent
- Route discovery queries to the Discovery Agent
- Handle ambiguous queries (default to Discovery, but suggest Governance if relevant)

### 6. Governance Score Calculation
- Weight rules by severity: critical (3x), warning (2x), info (1x)
- Score = passed weight / total weight × 100
- Categorize: Excellent (90+), Good (75-89), Needs Improvement (50-74), Poor (<50)

## Testing & Acceptance Criteria
- [ ] Governance Agent responds to compliance queries
- [ ] Compliance checker evaluates all defined rules correctly
- [ ] Governance score calculation is accurate
- [ ] Agent provides specific remediation guidance per failing rule
- [ ] Agent router correctly dispatches governance queries
- [ ] Non-compliant API listing works with filtering by rule
- [ ] Agent handles APIs with perfect compliance gracefully
- [ ] Agent handles APIs with no metadata (many failures) gracefully
- [ ] Unit tests cover all governance rules
- [ ] Unit tests cover score calculation edge cases

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
**Task**: Implement plan step 021 — Multi-Agent Architecture: Governance & Compliance Agent.

Read the full task specification at `docs/project/plan/021-governance-agent.md`.

Reference `docs/project/plan/020-foundry-agent-setup.md` for the agent framework and router, `docs/project/plan/007-api-center-data-layer.md` for the API data source, and `docs/project/apic_product_charter.md` for the governance goals.

Create the Governance Agent with a configurable rules engine (metadata completeness, versioning, spec quality, lifecycle, security, documentation rules), governance score calculation, and tools for compliance checking and remediation guidance. Update the agent router to dispatch governance-related queries.

Write unit tests for all governance rules, score calculation, and agent routing using pytest. Verify all tests pass with `uv run pytest`.

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/021-governance-agent.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
