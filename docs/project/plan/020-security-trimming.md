# 020 - Phase 1 MVP: Security Trimming Implementation

> **🔲 Status: Not Started**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References

- [Architecture Document](../apic_architecture.md) — Security: RBAC + security trimming
- [Product Charter](../apic_product_charter.md) — Stakeholders: Developers, API Owners, Platform Teams (different access levels)
- [Product Spec](../apic_portal_spec.md) — Access control requirements

## Overview

Implement security trimming so that API catalog results, search results, and AI chat responses only include APIs that the authenticated user is authorized to view. This ensures data isolation based on user roles and organizational boundaries.

## Dependencies

- **009** — API Center data layer (data source)
- **014** — Search API (needs trimming in search results)
- **017** — OpenAI integration (needs trimming in RAG context)
- **008** — Entra ID authentication (user identity and roles)

## Implementation Details

### 1. Security Trimming Strategy

Define the trimming model:

- APIs in API Center have metadata indicating access groups/teams
- User's Entra ID group memberships determine which APIs they can see
- Trimming applies at the BFF layer (before returning data to frontend)

### 2. User Context Service

```
src/bff/src/bff/services/
├── user_context_service.py         # User permissions and group membership
└── test_user_context_service.py
```

- Extract user groups from Entra ID token claims (or call Microsoft Graph API)
- Cache group membership per user session
- Provide a `canAccessApi(user, apiId)` check
- Provide a `getAccessibleApiFilter(user)` for bulk filtering

### 3. API Center Trimming

Update `api_catalog_service.py` (from task 009):

- Apply security filter before returning API lists
- Filter individual API access checks on detail views
- Return `403` if user requests an API they cannot access

### 4. Search Result Trimming

Update `search_service.py` (from task 017):

- Add security filter to AI Search queries
- Use AI Search's `$filter` parameter with user's accessible API IDs
- Ensure facet counts reflect only accessible APIs

### 5. Chat Context Trimming

Update `ai_chat_service.py` (from task 017):

- Filter RAG retrieval results to only include accessible APIs
- Ensure the AI cannot reference APIs the user cannot see
- Trim citations to accessible APIs only

### 6. Group Membership Caching

- Cache user → group mappings (TTL: 15 minutes)
- Cache group → API mappings (TTL: 5 minutes)
- Invalidation strategy: expire on access, refresh on miss

### 7. Admin Override

- Users with `Portal.Admin` role bypass security trimming
- Useful for platform team members who need full visibility

## Testing & Acceptance Criteria

- [ ] User A sees only APIs their groups have access to
- [ ] User B with different groups sees a different set of APIs
- [ ] Admin users see all APIs regardless of group membership
- [ ] Search results are filtered to accessible APIs only
- [ ] Facet counts reflect only accessible APIs
- [ ] Chat responses only reference accessible APIs
- [ ] Requesting an inaccessible API by ID returns 403
- [ ] Group membership is cached and refreshed appropriately
- [ ] Performance impact of security trimming is minimal (< 50ms added latency)
- [ ] Unit tests cover all trimming scenarios

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
**Task**: Implement plan step 020 — Security Trimming Implementation.

Read the full task specification at `docs/project/plan/020-security-trimming.md`.

Reference `docs/project/plan/008-entra-id-authentication.md` for the auth middleware and user context, `docs/project/plan/009-api-center-data-layer.md` for the catalog service, `docs/project/plan/014-search-api-implementation.md` for the search service, and `docs/project/plan/017-openai-integration.md` for the chat service.

Create a user context service that resolves group membership from Entra ID tokens. Update the catalog service, search service, and chat service to apply security trimming based on user permissions. Add admin bypass for `Portal.Admin` role. Implement group membership caching.

Write unit tests covering all trimming scenarios (different users, admin bypass, inaccessible APIs) using pytest. Verify all tests pass with `uv run pytest`.

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/020-security-trimming.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
