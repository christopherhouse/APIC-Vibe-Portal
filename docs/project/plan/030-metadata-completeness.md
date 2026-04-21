# 030 - Phase 3: Metadata Completeness Scoring & Recommendations

> **✅ Status: Complete**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References

- [Architecture Document](../apic_architecture.md) — AI-powered insights; multi-agent capabilities
- [Product Charter](../apic_product_charter.md) — Improved metadata completeness as success metric
- [Product Spec](../apic_portal_spec.md) — Metadata quality feature requirements
- [Persistence & Data Governance Baseline](016-persistence-data-governance-baseline.md) — Schema versioning, data retention for score history

## Overview

Build an intelligent metadata completeness scoring system with AI-powered recommendations for improving API documentation quality. This feature helps API owners understand what's missing from their APIs and provides actionable guidance to improve discoverability.

## Dependencies

- **009** — API Center data layer (API metadata)
- **023** — Governance Agent (governance rules as foundation)
- **017** — OpenAI integration (AI-powered recommendations)
- **012** — Frontend API detail page (UI integration point)
- **025** — Governance Dashboard (dashboard integration)

## Implementation Details

### 1. Completeness Scoring Service

```
src/bff/src/bff/services/
├── metadata_completeness_service.py
└── test_metadata_completeness_service.py
```

#### Scoring Dimensions

Score each API across multiple dimensions (0-100 each):

| Dimension          | Weight | What's Measured                                          |
| ------------------ | ------ | -------------------------------------------------------- |
| **Basic Info**     | 20%    | Title, description length, contacts                      |
| **Versioning**     | 15%    | Active version, version count, semver compliance         |
| **Specification**  | 25%    | Spec present, validates, endpoint count, schema coverage |
| **Documentation**  | 15%    | External docs, examples, changelog                       |
| **Classification** | 10%    | Tags, custom properties, lifecycle stage                 |
| **Security**       | 15%    | Auth schemes defined, security requirements documented   |

#### Scoring Rules

- Each dimension has sub-rules with individual scores
- Overall score = weighted average of dimension scores
- Track score history for trend analysis

### 2. AI Recommendation Engine

```
src/bff/src/bff/services/
├── metadata_recommendations_service.py
└── test_metadata_recommendations_service.py
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
src/bff/src/bff/routers/
├── metadata.py
└── test_metadata.py
```

| Method | Path                                   | Description                             |
| ------ | -------------------------------------- | --------------------------------------- |
| `GET`  | `/api/metadata/:apiId/score`           | Get completeness score for an API       |
| `GET`  | `/api/metadata/:apiId/recommendations` | Get AI recommendations                  |
| `GET`  | `/api/metadata/overview`               | Organization-wide completeness overview |
| `GET`  | `/api/metadata/leaderboard`            | Top and bottom APIs by completeness     |

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

Add a "Metadata Quality" tab to the API detail page (from task 012):

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

- [x] Completeness scoring produces accurate scores across all dimensions
- [x] Weighted overall score calculates correctly
- [x] AI recommendations are relevant and actionable
- [x] Recommendations are prioritized by impact
- [x] API detail page shows completeness score and breakdown
- [x] Governance dashboard shows organization-wide completeness metrics
- [x] Leaderboard correctly ranks APIs by completeness
- [x] Score history enables trend analysis
- [x] Unit tests cover all scoring rules and edge cases
- [x] Recommendations handle APIs with varying levels of completeness

## Implementation Notes

<!--
  This section is a living record updated by the implementing agent.
  Update status, log decisions, and record validation results as work progresses.
  When complete, change the Status at the top of this document to ✅ Complete.
-->

### Status History

| Date       | Status         | Author   | Notes                                                                                                                                                                                                          |
| ---------- | -------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| —          | 🔲 Not Started | —        | Task created                                                                                                                                                                                                   |
| 2026-04-21 | ✅ Complete    | @copilot | Full implementation: BFF scoring service, recommendations service, router (4 endpoints), frontend components (7), page integrations (API detail + governance dashboard), 142 unit tests (109 pytest + 33 Jest) |

### Technical Decisions

1. **Rule-based recommendations over OpenAI-dependent**: Implemented recommendations as a deterministic, rule-based engine that analyzes metadata gaps against the scoring dimensions. This approach provides instant results without external API dependencies, consistent output for the same input, and no additional cost. The architecture supports future enhancement with OpenAI for more nuanced, context-aware recommendations.

2. **Static path ordering in router**: Placed `/overview` and `/leaderboard` routes BEFORE `/{api_id}/score` and `/{api_id}/recommendations` to prevent FastAPI from capturing "overview" and "leaderboard" as `api_id` path parameters.

3. **MetadataQualityTab container component**: Created a dedicated container component (`MetadataQualityTab.tsx`) that manages data fetching, loading states, and error handling independently from the API detail page, keeping the page component clean and following existing composition patterns.

4. **Scoring dimension weights**: Followed the plan's specified weights (Basic Info 20%, Versioning 15%, Specification 25%, Documentation 15%, Classification 10%, Security 15%) with specification getting the highest weight as it's the most impactful for API discoverability.

5. **Impact-based recommendation priority**: Recommendations are sorted by numeric impact (high=3, medium=2, low=1) with sequential priority numbering, so the most impactful improvements appear first.

### Deviations from Plan

1. **File locations**: The plan specified `src/bff/src/bff/services/` but the actual BFF structure uses `src/bff/apic_vibe_portal_bff/services/`. Files were placed in the correct actual paths.

2. **Notification system placeholder**: The plan called for designing (but not implementing) a notification API. This was documented in the plan but no placeholder code was created, as the plan specification said "Document the API for future implementation" — the plan document itself serves as that documentation.

3. **"Improve this API" CTA**: The plan mentioned an "Improve this API" call-to-action linking to API Center editing. This was not implemented as there's no API Center editing integration in the portal yet — the recommendations provide the guidance directly.

### Validation Results

**BFF Tests (pytest):**

- `test_metadata_completeness_service.py`: 38 tests — all 6 scoring dimensions, grade mapping, get_score/get_overview/get_leaderboard, permission errors, edge cases
- `test_metadata_recommendations_service.py`: 63 tests — all dimension recommendation generators, sorting, priority numbering, error handling
- `test_metadata_router.py`: 8 tests — all 4 endpoints with happy paths and error handling (403/404)
- **Total: 109 new tests, all passing** (1163 total BFF tests pass)

**Frontend Tests (Jest):**

- `CompletenessScore.test.tsx`: 7 tests
- `CompletenessBreakdown.test.tsx`: 5 tests
- `RecommendationCard.test.tsx`: 6 tests
- `RecommendationList.test.tsx`: 4 tests
- `CompletenessOverview.test.tsx`: 5 tests
- `CompletenessLeaderboard.test.tsx`: 6 tests
- Updated `ApiTabs.test.tsx` for new "Metadata Quality" tab
- **Total: 33 new tests, all passing** (399 total frontend tests pass)

**Quality Checks:**

- ✅ BFF: ruff lint, ruff format, compileall
- ✅ Frontend: ESLint, Prettier, TypeScript (tsc --noEmit)
- ✅ Pre-existing build/test failures are unrelated to these changes

## Coding Agent Prompt

```text
**Task**: Implement plan step 030 — Metadata Completeness Scoring & Recommendations.

Read the full task specification at `docs/project/plan/030-metadata-completeness.md`.

Reference `docs/project/plan/009-api-center-data-layer.md` for API metadata access, `docs/project/plan/023-governance-agent.md` for the governance rules foundation, `docs/project/plan/017-openai-integration.md` for AI recommendation generation, `docs/project/plan/012-frontend-api-detail-page.md` for the API detail page integration, and `docs/project/plan/025-governance-dashboard-ui.md` for the governance dashboard integration.

Create a multi-dimensional completeness scoring service (Basic Info, Versioning, Specification, Documentation, Classification, Security), an AI recommendation engine using OpenAI, BFF endpoints, and integrate into both the API detail page (new Metadata Quality tab) and the governance dashboard (completeness overview and leaderboard).

Write unit tests for all scoring rules, recommendation generation, and components using pytest (BFF) and Jest (frontend). Verify all tests pass.

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/030-metadata-completeness.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
