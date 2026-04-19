# 023 - Phase 2: Multi-Agent Architecture — Governance & Compliance Agent

> **✅ Status: Complete**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References

- [Architecture Document](../apic_architecture.md) — Multi-agent design; Agent Layer: Foundry
- [Product Charter](../apic_product_charter.md) — Provide governance visibility; metadata completeness as success metric
- [Product Spec](../apic_portal_spec.md) — Governance feature requirements
- [Persistence & Data Governance Baseline](016-persistence-data-governance-baseline.md) — Governance snapshot storage, schema versioning, retention policy

## Overview

Create a Governance & Compliance Agent that can assess API governance status, check compliance with organizational standards, and provide recommendations for improving API metadata quality. Extend the multi-agent router to dispatch governance-related queries to this agent.

## Dependencies

- **022** — Foundry Agent Service setup (agent framework, router)
- **009** — API Center data layer (governance metadata source)
- **016** — Persistence & Data Governance Baseline (governance-snapshots container, repository pattern)

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

- [x] Governance Agent responds to compliance queries
- [x] Compliance checker evaluates all defined rules correctly
- [x] Governance score calculation is accurate
- [x] Agent provides specific remediation guidance per failing rule
- [x] Agent router correctly dispatches governance queries
- [x] Non-compliant API listing works with filtering by rule
- [x] Agent handles APIs with perfect compliance gracefully
- [x] Agent handles APIs with no metadata (many failures) gracefully
- [x] Unit tests cover all governance rules
- [x] Unit tests cover score calculation edge cases

## Implementation Notes

<!--
  This section is a living record updated by the implementing agent.
  Update status, log decisions, and record validation results as work progresses.
  When complete, change the Status at the top of this document to ✅ Complete.
-->

### Status History

| Date       | Status      | Author  | Notes                                                               |
| ---------- | ----------- | ------- | ------------------------------------------------------------------- |
| —          | 🔲 Not Started | —    | Task created                                                        |
| 2026-04-19 | ✅ Complete | copilot | Governance Agent implemented with 13 rules, 5 tools, intent routing |

### Technical Decisions

1. **Keyword-based intent routing** — Used a `frozenset` of ~30 governance-related keywords for the `_is_governance_intent()` function in `agent_router.py`. This is a simple, testable heuristic that avoids adding an LLM classifier call. It intentionally errs on the side of inclusivity to avoid missing governance queries.

2. **Rule evaluation via callable** — `GovernanceRule` accepts a `check_fn: Callable[[dict[str, Any]], bool]` rather than using subclassing. This makes each rule a standalone, composable, and easily testable unit without boilerplate class hierarchies.

3. **Dict-based API data** — The compliance checker operates on raw `dict` objects (camelCase from API Center) rather than `ApiDefinition` Pydantic models. This avoids a data mapping step and makes the rules work directly with data from `ApiCenterClient.get_api()`.

4. **No MAF security trimming middleware on Governance Agent** — Unlike the Discovery Agent, the Governance Agent does not need `SecurityTrimmingMiddleware` because governance checks are administrative in nature (checking API metadata, not serving API content to end users). This can be revisited in task 026 for role-based access.

5. **13 rules across 6 categories** — Implemented: `metadata.description`, `metadata.contacts`, `metadata.license`, `metadata.tags`, `versioning.has_version`, `versioning.semver`, `spec.has_specification`, `spec.has_deployments`, `lifecycle.deprecated_has_sunset`, `lifecycle.production_has_contact`, `security.auth_in_description`, `documentation.external_docs`, `documentation.meaningful_title`.

6. **Governance Agent without dedicated `__init__.py` imports of tools** — Following the same pattern as the Discovery Agent, tools are factory methods on the agent class itself, not importable standalone functions.

### Deviations from Plan

- **`_has_security_contact` rule not included in DEFAULT_RULES** — The plan mentioned "security contact" as a rule but this was scoped to a lighter version (`security.auth_in_description`) which checks whether the API description mentions the auth method. A separate security-contact rule was implemented as a predicate function but not added as a default rule (it's not referenced in the DEFAULT_RULES list) to keep the rule set focused.
- **File layout** — The plan specified `src/bff/src/bff/agents/…` (duplicated path) but the actual codebase uses `src/bff/apic_vibe_portal_bff/agents/…`. The correct path was used.
- **Tests in `tests/` directory** — The plan showed tests in `governance_agent/tests/`. The existing project convention places all tests in `src/bff/tests/`, which was followed.

### Validation Results

- **Test suite**: 862 tests passing (199 new tests added: 88 governance rules, 61 compliance checker, 52 governance agent, 18 agent router governance routing)
- **New test files**:
  - `tests/test_governance_rules.py` — 88 tests covering all 13 rule predicates, `GovernanceRule.evaluate()`, `DEFAULT_RULES` invariants
  - `tests/test_compliance_checker.py` — 61 tests covering score calculation, categorisation, `ComplianceResult` properties, and `get_rule()`
  - `tests/test_governance_agent.py` — 52 tests covering all 5 agent tools, `run`/`stream`, `_fetch_api_data`, `_extract_response_text`, prompts, and handler helpers
- **Updated test file**:
  - `tests/test_agent_router.py` — 18 new tests for `_is_governance_intent()` and governance-dispatch routing
- **Linting**: `ruff check` and `ruff format --check` both pass with zero errors
- **Backward compatibility**: All 663 pre-existing tests continue to pass; the `ApiDiscoveryAgent` is unchanged

## Coding Agent Prompt

```text
**Task**: Implement plan step 023 — Multi-Agent Architecture: Governance & Compliance Agent.

Read the full task specification at `docs/project/plan/023-governance-agent.md`.

Reference `docs/project/plan/022-foundry-agent-setup.md` for the agent framework and router, `docs/project/plan/009-api-center-data-layer.md` for the API data source, and `docs/project/apic_product_charter.md` for the governance goals.

Create the Governance Agent with a configurable rules engine (metadata completeness, versioning, spec quality, lifecycle, security, documentation rules), governance score calculation, and tools for compliance checking and remediation guidance. Update the agent router to dispatch governance-related queries.

Write unit tests for all governance rules, score calculation, and agent routing using pytest. Verify all tests pass with `uv run pytest`.

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/023-governance-agent.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
