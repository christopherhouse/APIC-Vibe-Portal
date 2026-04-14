# 025 - Phase 2: Integration Testing & Phase 2 Polish

> **🔲 Status: Not Started**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References
- [Architecture Document](../apic_architecture.md) — Full system with multi-agent orchestration
- [Product Charter](../apic_product_charter.md) — Phase 2: Governance + Compare delivery
- [Product Spec](../apic_portal_spec.md) — Phase 2 feature completeness

## Overview
Validate all Phase 2 features (governance, comparison, multi-agent) work together with the MVP features. Extend E2E tests, perform quality improvements, and ensure a cohesive user experience across all features.

## Dependencies
- **019** — MVP E2E tests (extend existing test suite)
- **020-024** — All Phase 2 features

## Implementation Details

### 1. Extended E2E Tests
Add to existing Playwright test suite:
```
e2e/tests/
├── governance-dashboard.spec.ts   # Governance feature tests
├── api-comparison.spec.ts         # Comparison feature tests
├── multi-agent-chat.spec.ts       # Multi-agent conversation tests
├── agent-admin.spec.ts            # Agent management tests
└── phase2-journey.spec.ts         # Full Phase 2 user journey
```

### 2. E2E Test Scenarios

#### Governance Dashboard
- Navigate to governance dashboard → see KPI cards with scores
- View score distribution chart → verify correct data
- Sort API scores table by score → see lowest first
- Click an API → see compliance detail with rule results
- View remediation for a failing rule → see actionable guidance

#### API Comparison
- Select 2 APIs from catalog → see comparison table
- Add a third API → comparison updates with 3 columns
- Remove an API → comparison updates correctly
- View AI analysis → meaningful narrative comparison
- Comparison URL is shareable

#### Multi-Agent Chat
- Ask a discovery question → Discovery Agent responds
- Ask a governance question → Agent hand-off occurs seamlessly
- Conversation context is maintained after hand-off
- Ask to compare APIs → agent uses comparison tools
- Low-confidence query → appropriate fallback handling

#### Agent Admin (Admin User)
- Login as admin → see agent management in navigation
- View agent list → see all registered agents
- View agent stats → usage metrics displayed
- Non-admin user → admin routes return 403

#### Phase 2 Full Journey
- Login → Browse catalog → Check governance dashboard → View failing API → Ask Governance Agent for help → Compare two APIs → View AI comparison → Logout

### 3. Phase 2 Polish
- [ ] Governance dashboard charts render correctly at all screen sizes
- [ ] Comparison table handles varying API metadata gracefully
- [ ] Agent transitions are smooth with visual feedback
- [ ] Navigation updates to include Governance and Compare sections
- [ ] Breadcrumbs work correctly on new pages
- [ ] All new pages have proper titles and meta tags
- [ ] Loading states for governance calculations and AI comparisons
- [ ] Error states for failed governance scoring or comparison

### 4. Performance Review
- Governance dashboard initial load time (target: < 3s)
- Comparison data generation time (target: < 5s for 3 APIs)
- Agent routing latency (target: < 500ms)
- Agent hand-off transition time (target: < 2s)

### 5. Navigation Update
- Add "Governance" to main navigation
- Add "Compare" to main navigation
- Update sidebar with Phase 2 sections
- Active state indicators for current page

## Testing & Acceptance Criteria
- [ ] All Phase 2 E2E tests pass on all browsers
- [ ] Governance dashboard loads within performance targets
- [ ] API comparison works for 2-5 APIs
- [ ] Multi-agent conversations flow naturally with hand-offs
- [ ] Admin features are properly gated
- [ ] Navigation includes all Phase 2 pages
- [ ] All new features integrate with existing MVP features
- [ ] No regressions in Phase 1 functionality (all Phase 1 E2E tests still pass)
- [ ] Performance targets are met

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
**Task**: Implement plan step 025 — Phase 2 Integration Testing & Polish.

Read the full task specification at `docs/project/plan/025-phase2-integration-testing.md`.

This task validates all Phase 2 features (tasks 020-024) work together with Phase 1. Reference the full plan directory at `docs/project/plan/` for all features to test.

Extend the Playwright E2E suite with tests for: governance dashboard, API comparison, multi-agent chat with hand-offs, and admin features. Add a complete Phase 2 user journey test. Update navigation to include Phase 2 pages. Polish loading/error states and responsive design.

Run all E2E tests (Phase 1 + Phase 2) and fix any issues. Verify no regressions in Phase 1 functionality.

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/025-phase2-integration-testing.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
