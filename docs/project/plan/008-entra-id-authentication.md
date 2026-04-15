# 008 - Phase 1 MVP: Entra ID Authentication Integration

> **✅ Status: Complete**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References
- [Architecture Document](../apic_architecture.md) — Security: Entra ID; RBAC + security trimming
- [Product Charter](../apic_product_charter.md) — Stakeholders: Developers, API Owners, Platform Teams (role-based access)
- [Product Spec](../apic_portal_spec.md) — Authentication and authorization requirements

## Overview
Integrate Microsoft Entra ID (Azure AD) authentication across both the frontend and BFF. This enables secure user login, role-based access control, and prepares for security trimming in later tasks.

## Dependencies
- **002** — Azure infrastructure (Entra ID app registrations)
- **005** — Frontend project setup (auth placeholder in layout)
- **006** — BFF API project setup (auth middleware placeholder)

## Implementation Details

### 1. Entra ID App Registrations
Document (and optionally script) the creation of two app registrations:
- **Frontend SPA App**: Public SPA client, configure redirect URI(s) for the frontend URL, use Authorization Code flow with PKCE via MSAL, and do not enable implicit grant
- **BFF API App**: Confidential client, expose API with scopes, configure API permissions

Configure:
- Frontend app requests token for BFF API scope
- BFF validates tokens from frontend
- Define app roles: `Portal.User`, `Portal.Admin`, `API.Owner`

### 2. Frontend Authentication (MSAL)
```
src/frontend/
├── lib/
│   ├── auth/
│   │   ├── msal-config.ts      # MSAL configuration
│   │   ├── auth-provider.tsx    # MSAL React provider
│   │   ├── use-auth.ts         # Custom auth hook
│   │   └── auth-guard.tsx      # Protected route component
│   └── api-client.ts           # Update to inject auth token
```

- Use `@azure/msal-react` and `@azure/msal-browser`
- Configure MSAL with frontend app registration
- Wrap app in `MsalProvider` in root layout
- Create `useAuth()` hook exposing: `isAuthenticated`, `user`, `login`, `logout`, `getToken`
- Create `AuthGuard` component for protected routes
- Update API client to inject Bearer token in requests

### 3. Frontend Auth UI
- **Login button**: In header, triggers MSAL redirect/popup login
- **User avatar/menu**: After login, show user name, email, avatar
- **Logout option**: In user dropdown menu
- **Protected routes**: `/catalog`, `/chat` require authentication
- **Login page**: Optional branded login page with "Sign in with Microsoft" button
- **Loading state**: Show loading indicator during auth redirect

### 4. BFF Authentication Middleware
```
src/bff/src/bff/middleware/
├── auth.py                 # JWT validation middleware (replace placeholder)
└── test_auth.py
```

- Validate JWT tokens from Entra ID using `python-jose` (or `PyJWT`) and JWKS
- Fetch signing keys from Entra ID discovery endpoint
- Validate: issuer, audience, expiration, signature
- Extract user claims: `oid`, `name`, `email`, `roles`
- Attach user context to request state (FastAPI dependency injection)
- Return `401` for missing/invalid tokens
- Return `403` for insufficient roles

### 5. Role-Based Access Control (BFF)
```
src/bff/src/bff/middleware/
├── rbac.py                 # Role checking middleware (FastAPI dependencies)
└── test_rbac.py
```

- `require_role(role: str)` FastAPI dependency factory
- `require_any_role(roles: list[str])` FastAPI dependency factory
- Apply to routes as needed (most routes require `Portal.User`)
- Admin endpoints require `Portal.Admin`

### 6. Configuration
Frontend environment variables:
- `NEXT_PUBLIC_MSAL_CLIENT_ID`
- `NEXT_PUBLIC_MSAL_AUTHORITY`
- `NEXT_PUBLIC_MSAL_REDIRECT_URI`
- `NEXT_PUBLIC_BFF_API_SCOPE`

BFF environment variables:
- `ENTRA_TENANT_ID`
- `ENTRA_CLIENT_ID`
- `ENTRA_AUDIENCE`

## Testing & Acceptance Criteria
- [ ] Unauthenticated users are redirected to login
- [ ] Login via Entra ID works (redirect flow)
- [ ] After login, user info displays in the header
- [ ] Logout clears session and redirects to login
- [ ] API requests include Bearer token
- [ ] BFF rejects requests without valid tokens (401)
- [ ] BFF rejects requests with insufficient roles (403)
- [ ] Token refresh works silently before expiration
- [ ] MSAL configuration matches app registration settings
- [ ] Auth middleware has comprehensive unit tests (valid token, expired token, wrong audience, missing roles)
- [ ] Protected routes redirect unauthenticated users

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
| 2026-04-15 | ✅ Complete | copilot | Implemented Entra ID auth across frontend (MSAL React v5) and BFF (PyJWT + JWKS). 94 BFF tests, 66 frontend tests all passing. |

### Technical Decisions
- **MSAL v5**: Used `@azure/msal-browser` v5.6.3 and `@azure/msal-react` v5.2.1 (latest major) instead of v4.x as specified in the plan. MSAL v5 removed several deprecated options (`navigateToLoginRequestUrl`, `storeAuthStateInCookie`, `InteractionStatus.Login`).
- **PyJWT over python-jose**: Used `PyJWT>=2.12.0` with `cryptography>=46.0.5` for JWT validation. PyJWT is actively maintained and is the recommended library for JWT decoding. Security advisory for PyJWT < 2.12.0 (unknown crit header extensions) was resolved by requiring >= 2.12.0.
- **cachetools for JWKS caching**: Added `cachetools>=5.5.0` for TTL-based caching of the JWKS client (24-hour TTL).
- **Token provider pattern for API client**: Used a `setTokenProvider()` registration pattern in the API client to decouple the MSAL dependency from the fetch wrapper, enabling easier testing and server-side rendering compatibility.
- **Auth middleware pass-through in dev**: When `entra_tenant_id` is empty (local development), the auth middleware passes all requests through without authentication.
- **B008 ruff rule ignored**: Added B008 to ruff ignore list since `Depends()` in function defaults is the standard FastAPI dependency injection pattern.
- **RBAC via FastAPI dependencies**: Implemented role checks as dependency factories (`require_role`, `require_any_role`) rather than middleware, allowing per-route role requirements.

### Deviations from Plan
- **MSAL v5 instead of v4**: The plan referenced `@azure/msal-react` v3.x/v4.x, but v5 is the current major version. API changes required removing deprecated options.
- **No separate login page**: A branded login page was listed as optional in the plan. Instead, the Sign In button in the header triggers MSAL redirect flow directly, which is the standard SPA pattern.
- **Task references**: The plan document and some code placeholders referenced "task 016" instead of "task 008" for this auth integration. Updated all references to align with the actual task number.
- **File structure**: `test_auth.py` and `test_rbac.py` placed in `tests/middleware/` directory (following existing test conventions) rather than alongside the source files as shown in the plan.

### Validation Results
- **BFF tests**: 94 tests passing (including 10 auth middleware tests, 8 RBAC tests)
- **Frontend tests**: 66 tests passing (including 6 msal-config tests, 8 useAuth tests, 6 AuthGuard tests, 3 api-client tests)
- **Frontend lint**: ESLint clean (0 errors, 0 warnings)
- **BFF lint**: Ruff clean (0 errors)
- **Frontend build**: Next.js build successful (TypeScript type-checks pass)
- **Auth middleware coverage**: Valid token, expired token, wrong audience, wrong issuer, missing auth header, invalid format, unconfigured tenant passthrough
- **RBAC coverage**: User with correct role allowed, user without role rejected (403), unauthenticated user rejected (401), multi-role (any) checks
- **AuthGuard coverage**: Loading state, redirect to login, protected content rendering, role-based access denied, custom fallback


## Coding Agent Prompt

```text
**Task**: Implement plan step 008 — Entra ID Authentication Integration.

Read the full task specification at `docs/project/plan/008-entra-id-authentication.md`.

Reference the architecture at `docs/project/apic_architecture.md` (Security: Entra ID, RBAC), `docs/project/plan/005-frontend-nextjs-setup.md` for the frontend layout, and `docs/project/plan/006-bff-api-setup.md` for the BFF middleware placeholder.

In the frontend, integrate MSAL React for Entra ID authentication with login/logout UI, protected routes via AuthGuard, a useAuth hook, and update the API client to inject Bearer tokens. In the BFF, implement JWT validation middleware using JWKS (via `python-jose` or `PyJWT`), role-based access control as FastAPI dependencies, and apply auth to all API routes.

Write unit tests for auth middleware, RBAC middleware, and auth-related frontend components. Verify all tests pass.

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/008-entra-id-authentication.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
