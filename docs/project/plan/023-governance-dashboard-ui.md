# 023 - Phase 2: Governance Dashboard UI

> **🔲 Status: Not Started**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References
- [Architecture Document](../apic_architecture.md) — Frontend: Next.js SPA; governance visibility
- [Product Charter](../apic_product_charter.md) — Provide governance visibility; metadata completeness as success metric
- [Product Spec](../apic_portal_spec.md) — Governance dashboard requirements

## Overview
Build the governance dashboard in the frontend that provides a visual overview of API governance health across the organization. This includes compliance scores, trend indicators, and drill-down capabilities to identify and remediate governance issues.

## Dependencies
- **004** — Frontend project setup
- **021** — Governance Agent (governance scoring and compliance data)
- **008** — BFF API catalog endpoints (API listing data)

## Implementation Details

### 1. Governance BFF Endpoints
```
src/bff/src/bff/routers/
├── governance.py                   # Governance dashboard endpoints (FastAPI router)
└── test_governance.py
```

Endpoints:
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/governance/summary` | Overall governance summary |
| `GET` | `/api/governance/scores` | All API governance scores |
| `GET` | `/api/governance/rules` | Available governance rules |
| `GET` | `/api/governance/apis/:apiId/compliance` | Single API compliance report |
| `GET` | `/api/governance/trends` | Governance score trends over time |

### 2. Governance Summary Service
```
src/bff/src/bff/services/
├── governance_dashboard_service.py
└── test_governance_dashboard_service.py
```

- Aggregate governance scores across all APIs
- Calculate organization-wide compliance rates per rule
- Identify top compliance issues
- Track score trends (store periodic snapshots)

### 3. Frontend Dashboard Page
```
app/governance/
├── page.tsx                # Governance dashboard
├── loading.tsx
├── [apiId]/
│   └── page.tsx            # Single API compliance detail
└── components/
    ├── GovernanceOverview.tsx       # KPI cards (overall score, compliant count)
    ├── ScoreDistribution.tsx       # Score distribution chart
    ├── RuleComplianceChart.tsx     # Compliance rate per rule (bar chart)
    ├── TopIssues.tsx               # Most common failing rules
    ├── ApiScoreTable.tsx           # Sortable table of all API scores
    ├── ApiComplianceDetail.tsx     # Single API compliance breakdown
    ├── GovernanceTrend.tsx         # Score trend over time chart
    └── RemediationPanel.tsx        # Remediation guidance panel
```

### 4. Dashboard Overview
Top-level KPI cards:
- **Overall Score**: Average governance score across all APIs (with trend arrow)
- **Compliant APIs**: Count/percentage meeting minimum threshold (e.g., score ≥ 75)
- **Critical Issues**: Count of APIs with critical rule failures
- **Improvement**: Score change over last 30 days

### 5. Visualizations
- **Score Distribution**: Histogram or donut chart showing APIs by score range (Excellent/Good/Needs Improvement/Poor)
- **Rule Compliance**: Horizontal bar chart showing compliance rate per governance rule
- **Trend Chart**: Line chart showing average score over time (weekly/monthly)
- Use a charting library: `recharts`, `chart.js`, or `nivo`

### 6. API Scores Table
- Sortable table with columns: API Name, Score, Status, Top Issues, Last Checked
- Color-coded score badges (green/yellow/orange/red)
- Filter by score range, status, specific failing rule
- Click row to drill into API compliance detail
- Export to CSV option

### 7. Single API Compliance Detail (`/governance/:apiId`)
- Header with API name and overall score
- Rule-by-rule breakdown:
  - Rule name, description
  - Pass/Fail status with icon
  - Severity indicator
  - Remediation guidance (expandable)
- Link to API detail page for editing (API Center)
- "Ask Governance Agent" button (opens chat with context)

### 8. Remediation Panel
- When a failing rule is selected, show:
  - What is required
  - Current state of the API metadata
  - Step-by-step remediation instructions
  - Link to relevant documentation

## Testing & Acceptance Criteria
- [ ] Dashboard overview shows accurate KPI cards
- [ ] Score distribution chart renders correctly
- [ ] Rule compliance chart shows per-rule compliance rates
- [ ] API scores table is sortable and filterable
- [ ] Clicking an API navigates to compliance detail
- [ ] Single API compliance detail shows rule-by-rule breakdown
- [ ] Remediation guidance is actionable and specific
- [ ] Trend chart displays score changes over time
- [ ] All visualizations handle empty data gracefully
- [ ] Dashboard is responsive across screen sizes
- [ ] All components have unit tests
- [ ] BFF governance endpoints return correct aggregated data

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
**Task**: Implement plan step 023 — Governance Dashboard UI.

Read the full task specification at `docs/project/plan/023-governance-dashboard-ui.md`.

Reference `docs/project/plan/021-governance-agent.md` for the governance scoring system and rules, `docs/project/plan/004-frontend-nextjs-setup.md` for the frontend structure, and `docs/project/apic_product_charter.md` for the governance visibility goals.

Create BFF endpoints for governance summary, scores, and compliance data. Build the `/governance` dashboard page with KPI cards, score distribution chart, rule compliance chart, trend chart, sortable API scores table, and single-API compliance drill-down with remediation guidance. Use a charting library (recharts or similar).

Write unit tests for all components and BFF endpoints. Verify the build succeeds, linting passes, and all tests pass.

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/023-governance-dashboard-ui.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
