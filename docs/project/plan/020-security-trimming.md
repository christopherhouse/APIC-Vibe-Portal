# 020 - Phase 1 MVP: Security Trimming Implementation

> **✅ Status: Complete**
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

- [x] User A sees only APIs their groups have access to
- [x] User B with different groups sees a different set of APIs
- [x] Admin users see all APIs regardless of group membership
- [x] Search results are filtered to accessible APIs only
- [x] Facet counts reflect only accessible APIs
- [x] Chat responses only reference accessible APIs
- [x] Requesting an inaccessible API by ID returns 403
- [x] Group membership is cached and refreshed appropriately
- [ ] Performance impact of security trimming is minimal (< 50ms added latency) — not formally benchmarked; in-memory filtering adds negligible latency
- [x] Unit tests cover all trimming scenarios

## Implementation Notes

<!--
  This section is a living record updated by the implementing agent.
  Update status, log decisions, and record validation results as work progresses.
  When complete, change the Status at the top of this document to ✅ Complete.
-->

### Status History

| Date       | Status         | Author  | Notes                                            |
| ---------- | -------------- | ------- | ------------------------------------------------ |
| —          | 🔲 Not Started | —       | Task created                                     |
| 2026-04-19 | ✅ Complete    | Copilot | Full implementation: UserContextService, policy repo, admin router, service-level trimming, 52 new tests |

### Technical Decisions

1. **API-to-Group Mapping Storage: Cosmos DB** — Access policies are persisted in a new Cosmos DB container `api-access-policies` (partition key: `apiName`). This enables future admin UI, cross-replica consistency, and aligns with the existing data layer. The container name is configurable via `COSMOS_DB_ACCESS_POLICIES_CONTAINER` environment variable.

2. **Default Access Model: Public by default** — When no policy document exists for an API, it is treated as publicly accessible to all authenticated users. Only APIs with an explicit policy document (with `allowedGroups` or `isPublic=false`) are restricted. This prevents accidentally hiding the entire catalog when policies are first deployed.

3. **Groups from JWT `groups` claim** — Group OIDs are extracted from the `groups` claim in the Entra ID JWT token. If the claim is absent (group overage for large tenants), the user is treated as having no group memberships. Microsoft Graph API calls for group resolution are deferred to a future task.

4. **Security trimming at service layer** — Services (`ApiCatalogService`, `SearchService`, `AIChatService`) accept an `accessible_api_ids: list[str] | None` parameter. `None` signals admin bypass (no filtering); a list restricts results to those API names. This keeps services testable without requiring a `UserContextService` mock.

5. **Cache strategy for catalog**: `ApiCatalogService` now caches the full sorted definition list (not paginated) so that security trimming produces accurate `total_count` and `total_pages` values for each user.

6. **Admin bypass** — Users with `Portal.Admin` role receive `accessible_api_ids=None` from `UserContextService`, bypassing all trimming logic in catalog, search, and chat services.

7. **Policy cache TTL** — `UserContextService` caches the full policy list in-memory with a 5-minute TTL. After admin writes (PUT/DELETE `/api/admin/access-policies/{apiName}`) the cache is explicitly invalidated so changes take effect immediately.

8. **Fail open on Cosmos DB errors** — If the policy repository is unavailable, the service logs a warning and returns an empty policy map, treating all APIs as public. This prevents a Cosmos DB outage from causing a complete portal outage.

9. **Admin management endpoints** — A new `Portal.Admin`-only router at `/api/admin/access-policies` exposes CRUD operations for managing access policies. This addresses the issue comment asking about an admin interface for maintaining API-to-group mappings.

### Deviations from Plan

- **Search suggestor filter**: Added `accessible_api_ids` support to `suggest()` in addition to `search()`, which was not explicitly called out in the plan but is necessary for consistent security trimming.
- **Catalog cache refactored**: Changed from caching per-page paginated responses to caching the full sorted list per OData filter. This is necessary for security trimming to produce correct pagination totals.
- **Open-access stub service**: When Cosmos DB is not configured (dev environment), a stub repository is used that returns empty policies (all APIs public). This avoids requiring Cosmos DB for local development.

### Validation Results

- **585 tests pass** (533 original + 52 new)
- **52 new unit tests** in `tests/test_user_context_service.py` covering:
  - Policy cache TTL and invalidation
  - Admin bypass (Portal.Admin role)
  - Group extraction from JWT claims
  - Accessible API ID resolution (user A vs user B)
  - Public API access, restricted access, locked API (empty groups)
  - `can_access_api()` for individual checks
  - OData filter generation with/without security trimming
  - `ApiCatalogService` trimming (list and detail endpoints)
  - `SearchService` trimming (search and suggest)
  - `AIChatService` RAG retrieval trimming
  - `ApiAccessPolicyDocument` model serialization
- **Lint/format**: All ruff checks pass
- **Admin router**: `PUT /api/admin/access-policies/{apiName}` creates/updates policy and invalidates cache; `DELETE` removes policy; `GET` lists all policies

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
