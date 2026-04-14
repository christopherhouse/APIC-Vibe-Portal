# 016 - Phase 1 MVP: Entra ID Authentication Integration

## References
- [Architecture Document](../apic_architecture.md) — Security: Entra ID; RBAC + security trimming
- [Product Charter](../apic_product_charter.md) — Stakeholders: Developers, API Owners, Platform Teams (role-based access)
- [Product Spec](../apic_portal_spec.md) — Authentication and authorization requirements

## Overview
Integrate Microsoft Entra ID (Azure AD) authentication across both the frontend and BFF. This enables secure user login, role-based access control, and prepares for security trimming in later tasks.

## Dependencies
- **002** — Azure infrastructure (Entra ID app registrations)
- **004** — Frontend project setup (auth placeholder in layout)
- **005** — BFF API project setup (auth middleware placeholder)

## Implementation Details

### 1. Entra ID App Registrations
Document (and optionally script) the creation of two app registrations:
- **Frontend SPA App**: Public client, redirect URI to frontend URL, implicit grant for ID tokens
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
src/bff/src/middleware/
├── auth.ts                 # JWT validation middleware (replace placeholder)
└── auth.test.ts
```

- Validate JWT tokens from Entra ID using `jsonwebtoken` and JWKS
- Use `jwks-rsa` to fetch signing keys from Entra ID discovery endpoint
- Validate: issuer, audience, expiration, signature
- Extract user claims: `oid`, `name`, `email`, `roles`
- Attach user context to request object
- Return `401` for missing/invalid tokens
- Return `403` for insufficient roles

### 5. Role-Based Access Control (BFF)
```
src/bff/src/middleware/
├── rbac.ts                 # Role checking middleware
└── rbac.test.ts
```

- `requireRole(role: string)` middleware factory
- `requireAnyRole(roles: string[])` middleware factory
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

## Coding Agent Prompt

> **Task**: Implement plan step 016 — Entra ID Authentication Integration.
>
> Read the full task specification at `docs/project/plan/016-entra-id-authentication.md`.
>
> Reference the architecture at `docs/project/apic_architecture.md` (Security: Entra ID, RBAC), `docs/project/plan/004-frontend-nextjs-setup.md` for the frontend layout, and `docs/project/plan/005-bff-api-setup.md` for the BFF middleware placeholder.
>
> In the frontend, integrate MSAL React for Entra ID authentication with login/logout UI, protected routes via AuthGuard, a useAuth hook, and update the API client to inject Bearer tokens. In the BFF, implement JWT validation middleware using JWKS, role-based access control middleware, and apply auth to all API routes.
>
> Write unit tests for auth middleware, RBAC middleware, and auth-related frontend components. Verify the build succeeds and all tests pass.
