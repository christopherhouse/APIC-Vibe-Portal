# Authentication and RBAC

## Overview

Authentication uses **Microsoft Entra ID** (Azure AD). Authorization uses **App Roles** embedded in the JWT token's `roles` claim. There is no application-level user/role database — Entra ID is the single source of truth.

## Role Definitions

| Role Value          | Display Name | Description                                                                    | Typical Assignees               |
| ------------------- | ------------ | ------------------------------------------------------------------------------ | ------------------------------- |
| `Portal.Admin`      | Admin        | Full access — manage config, view org-wide analytics, bypass security trimming | Platform leads, DevOps managers |
| `Portal.Maintainer` | Maintainer   | Manage APIs — publish, edit, curate catalog; view scoped analytics             | API product owners, tech leads  |
| `Portal.User`       | User         | Read-only — browse catalog, use AI chat                                        | All developers                  |

> Roles are **additive**. A user can have multiple roles.

## How Authentication Works

```
Frontend (MSAL)
  │  1. Login redirect → Entra ID
  │  2. Receive JWT with `roles` claim
  ▼
BFF (FastAPI JWT middleware)
  │  3. Validate signature, issuer, audience
  │  4. Extract `roles` from token
  │  5. require_role() / require_any_role() per route
  │  6. Return 403 if role missing
  ▼
Response
```

## Route → Role Matrix

| Route                      | Required Roles      |
| -------------------------- | ------------------- |
| `GET /api/catalog/`        | Any portal role     |
| `POST /api/chat/`          | Any portal role     |
| `GET /api/governance/`     | Admin or Maintainer |
| `GET /api/analytics/`      | Admin or Maintainer |
| `GET /health`, `GET /docs` | Public (no auth)    |

## Entra ID Setup

### 1. Create App Registrations

You need **two** app registrations:

| Registration     | Purpose                                           |
| ---------------- | ------------------------------------------------- |
| **Frontend SPA** | MSAL login; requests tokens scoped to the BFF API |
| **BFF API**      | Exposes the API scope; defines App Roles          |

#### Frontend SPA

1. Azure Portal → Entra ID → App registrations → **New registration**
   - Name: `APIC Vibe Portal - Frontend`
   - Supported account types: Single tenant
   - Redirect URI: `http://localhost:3000` (SPA platform)
2. Under **Authentication**, add the production redirect URIs for each environment
3. Under **API permissions**, add a delegated permission to the BFF API scope

#### BFF API

1. Azure Portal → Entra ID → App registrations → **New registration**
   - Name: `APIC Vibe Portal - BFF`
   - Supported account types: Single tenant
2. Under **Expose an API**, set Application ID URI: `api://<client-id>`
3. Add scope: `access_as_user` (or `/.default`)

### 2. Define App Roles

In the **BFF API** registration → **App roles** → **Create app role**:

| Display Name | Value               | Allowed Member Types | Description                |
| ------------ | ------------------- | -------------------- | -------------------------- |
| Admin        | `Portal.Admin`      | Users/Groups         | Full portal administration |
| Maintainer   | `Portal.Maintainer` | Users/Groups         | API catalog management     |
| User         | `Portal.User`       | Users/Groups         | Read-only portal access    |

Or update the manifest JSON directly:

```json
"appRoles": [
  {
    "allowedMemberTypes": ["User", "Group"],
    "displayName": "Admin",
    "description": "Full portal administration",
    "isEnabled": true,
    "id": "<unique-guid>",
    "value": "Portal.Admin"
  },
  {
    "allowedMemberTypes": ["User", "Group"],
    "displayName": "Maintainer",
    "description": "API catalog management",
    "isEnabled": true,
    "id": "<unique-guid>",
    "value": "Portal.Maintainer"
  },
  {
    "allowedMemberTypes": ["User", "Group"],
    "displayName": "User",
    "description": "Read-only portal access",
    "isEnabled": true,
    "id": "<unique-guid>",
    "value": "Portal.User"
  }
]
```

### 3. Enable "Assignment Required"

In **Enterprise applications** (the BFF app's enterprise application):

- **Properties** → **Assignment required?** → **Yes**

This ensures only users explicitly assigned a role can log in.

### 4. Assign Users/Groups to Roles

**Enterprise applications** → **Users and groups** → **Add user/group** → select users → select role.

#### Recommended: Group-Based Assignment

| Security Group               | Role              |
| ---------------------------- | ----------------- |
| `sg-apic-portal-admins`      | Portal.Admin      |
| `sg-apic-portal-maintainers` | Portal.Maintainer |
| `sg-apic-portal-users`       | Portal.User       |

## Local Development Setup

```bash
# 1. Start BFF
cd src/bff && uv run fastapi dev

# 2. Start frontend
npm run dev --workspace=@apic-vibe-portal/frontend

# 3. Open http://localhost:3000 — redirects to Microsoft login
```

Assign yourself `Portal.Admin` in Entra ID for full local access.

## Code Examples

### BFF Route Protection

```python
from fastapi import Depends
from apic_vibe_portal_bff.middleware.rbac import require_role, require_any_role

# Any portal role
@router.get("/catalog", dependencies=[Depends(require_any_role(["Portal.User", "Portal.Admin", "Portal.Maintainer"]))])

# Admin only
@router.get("/admin/settings", dependencies=[Depends(require_role("Portal.Admin"))])

# Admin or Maintainer
@router.get("/catalog/edit", dependencies=[Depends(require_any_role(["Portal.Admin", "Portal.Maintainer"]))])
```

### Frontend Route Protection

```tsx
// Any authenticated user
<AuthGuard><CatalogPage /></AuthGuard>

// Admin only
<AuthGuard requiredRoles={['Portal.Admin']}><AdminPage /></AuthGuard>

// Admin or Maintainer
<AuthGuard requiredRoles={['Portal.Admin', 'Portal.Maintainer']}><CatalogEditPage /></AuthGuard>
```

## Troubleshooting

| Problem                              | Fix                                                                             |
| ------------------------------------ | ------------------------------------------------------------------------------- |
| `roles` claim is empty               | User has no role assignment in Enterprise applications → assign a role          |
| 403 on a route user should access    | Log out and back in to refresh token; verify role values match exactly          |
| AADSTS50105 — user can't log in      | "Assignment required" is on but user has no role; assign at least `Portal.User` |
| Roles not reflected after assignment | Role changes take effect on next token issuance; have user log out and back in  |

## Related

- [[Architecture]] — Security model and trust boundaries
- [[Security]] — Threat model and security controls
- [[Runtime Configuration]] — How MSAL config is injected at runtime
