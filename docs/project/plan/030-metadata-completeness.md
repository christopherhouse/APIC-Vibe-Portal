# 030 - Phase 3: Metadata Completeness Scoring & Recommendations

> **🔲 Status: Not Started**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References
- [Architecture Document](../apic_architecture.md) — AI-powered insights; multi-agent capabilities
- [Product Charter](../apic_product_charter.md) — Improved metadata completeness as success metric
- [Product Spec](../apic_portal_spec.md) — Metadata quality feature requirements

## Overview
Build an intelligent metadata completeness scoring system with AI-powered recommendations for improving API documentation quality. This feature helps API owners understand what's missing from their APIs and provides actionable guidance to improve discoverability.

## Dependencies
- **009** — API Center data layer (API metadata)
- **023** — Governance Agent (governance rules as foundation)
- **017** — OpenAI integration (AI-powered recommendations)

## Implementation Details

### 1. Completeness Scoring Service
```
src/bff/src/services/
├── metadata-completeness.service.ts
└── metadata-completeness.service.test.ts
```

#### Scoring Dimensions
Score each API across multiple dimensions (0-100 each):

| Dimension | Weight | What's Measured |
|-----------|--------|-----------------|
| **Basic Info** | 20% | Title, description length, contacts |
| **Versioning** | 15% | Active version, version count, semver compliance |
| **Specification** | 25% | Spec present, validates, endpoint count, schema coverage |
| **Documentation** | 15% | External docs, examples, changelog |
| **Classification** | 10% | Tags, custom properties, lifecycle stage |
| **Security** | 15% | Auth schemes defined, security requirements documented |

#### Scoring Rules
- Each dimension has sub-rules with individual scores
- Overall score = weighted average of dimension scores
- Track score history for trend analysis

### 2. AI Recommendation Engine
```
src/bff/src/services/
├── metadata-recommendations.service.ts
└── metadata-recommendations.service.test.ts
```

- Analyze metadata gaps for a specific API
- Generate prioritized improvement recommendations using OpenAI
- Recommendations include:
  - What to add/improve
  - Why it matters (discoverability impact)
  - Example of good metadata for this field
  - Estimated effort (low/medium/high)
- Cache recommendations per API (refresh on API update)

### 3. BFF Endpoints
```
src/bff/src/routes/
├── metadata.routes.ts
└── metadata.routes.test.ts
```

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/metadata/:apiId/score` | Get completeness score for an API |
| `GET` | `/api/metadata/:apiId/recommendations` | Get AI recommendations |
| `GET` | `/api/metadata/overview` | Organization-wide completeness overview |
| `GET` | `/api/metadata/leaderboard` | Top and bottom APIs by completeness |

### 4. Frontend Components
```
app/catalog/[apiId]/components/
├── CompletenessScore.tsx           # Score badge/ring on API detail
├── CompletenessBreakdown.tsx       # Dimension-by-dimension breakdown
├── RecommendationList.tsx          # AI recommendations list
└── RecommendationCard.tsx          # Individual recommendation card

app/governance/components/
├── CompletenessOverview.tsx        # Org-wide completeness metrics
└── CompletenessLeaderboard.tsx     # API leaderboard by completeness
```

### 5. API Detail Integration
Add a "Metadata Quality" tab to the API detail page (from task 010):
- Completeness score ring/gauge (with letter grade: A, B, C, D, F)
- Dimension breakdown with progress bars
- AI-generated recommendations list
- "Improve this API" call-to-action linking to API Center editing

### 6. Governance Dashboard Integration
Add to the governance dashboard (from task 023):
- Organization-wide average completeness score
- Completeness distribution chart
- Leaderboard: Top 5 most complete and Bottom 5 least complete APIs
- Trend: Average completeness over time

### 7. Notification System (Placeholder)
- Design (but don't implement) a notification system for:
  - API owners when their API's completeness drops below threshold
  - Weekly digest of metadata improvement suggestions
  - Document the API for future implementation

## Testing & Acceptance Criteria
- [ ] Completeness scoring produces accurate scores across all dimensions
- [ ] Weighted overall score calculates correctly
- [ ] AI recommendations are relevant and actionable
- [ ] Recommendations are prioritized by impact
- [ ] API detail page shows completeness score and breakdown
- [ ] Governance dashboard shows organization-wide completeness metrics
- [ ] Leaderboard correctly ranks APIs by completeness
- [ ] Score history enables trend analysis
- [ ] Unit tests cover all scoring rules and edge cases
- [ ] Recommendations handle APIs with varying levels of completeness

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
**Task**: Implement plan step 030 — Metadata Completeness Scoring & Recommendations.

Read the full task specification at `docs/project/plan/030-metadata-completeness.md`.

Reference `docs/project/plan/007-api-center-data-layer.md` for API metadata access, `docs/project/plan/021-governance-agent.md` for the governance rules foundation, `docs/project/plan/014-openai-integration.md` for AI recommendation generation, `docs/project/plan/010-frontend-api-detail-page.md` for the API detail page integration, and `docs/project/plan/023-governance-dashboard-ui.md` for the governance dashboard integration.

Create a multi-dimensional completeness scoring service (Basic Info, Versioning, Specification, Documentation, Classification, Security), an AI recommendation engine using OpenAI, BFF endpoints, and integrate into both the API detail page (new Metadata Quality tab) and the governance dashboard (completeness overview and leaderboard).

Write unit tests for all scoring rules, recommendation generation, and components. Verify the build succeeds and all tests pass.

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/030-metadata-completeness.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
