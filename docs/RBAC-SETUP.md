# RBAC Setup Guide — APIC Vibe Portal

This guide explains how to configure Role-Based Access Control (RBAC) for the APIC Vibe Portal using Microsoft Entra ID (Azure AD) App Roles.

> **First time setting up?** Start with the [Entra ID Setup Guide](ENTRA-SETUP.md) which walks through creating both app registrations (frontend SPA + BFF API), configuring scopes, permissions, and consent. Then return here for detailed role assignment and group management.

## Table of Contents

- [Role Definitions](#role-definitions)
- [How RBAC Works](#how-rbac-works)
- [Entra ID App Role Configuration](#entra-id-app-role-configuration)
  - [1. Define App Roles in the App Registration](#1-define-app-roles-in-the-app-registration)
  - [2. Enable User Assignment](#2-enable-user-assignment)
  - [3. Assign Users or Groups to Roles](#3-assign-users-or-groups-to-roles)
- [Group-Based Role Assignment (Recommended)](#group-based-role-assignment-recommended)
- [Local Development Setup](#local-development-setup)
  - [Prerequisites](#prerequisites)
  - [Step 1 — Create a Dev App Registration](#step-1--create-a-dev-app-registration)
  - [Step 2 — Add App Roles](#step-2--add-app-roles)
  - [Step 3 — Assign Yourself to a Role](#step-3--assign-yourself-to-a-role)
  - [Step 4 — Configure Environment Variables](#step-4--configure-environment-variables)
  - [Step 5 — Verify Locally](#step-5--verify-locally)
- [Deployed Environment Setup](#deployed-environment-setup)
- [Automating with Azure CLI / Microsoft Graph](#automating-with-azure-cli--microsoft-graph)
- [Role Hierarchy and Route Protection](#role-hierarchy-and-route-protection)
- [Troubleshooting](#troubleshooting)

---

## Role Definitions

The portal defines three roles. Each role controls what a user can see and do.

| Role Value          | Display Name  | Description                                                                                           | Typical Assignees                    |
| ------------------- | ------------- | ----------------------------------------------------------------------------------------------------- | ------------------------------------ |
| `Portal.Admin`      | Admin         | Full access — manage portal configuration, view organization-wide analytics, bypass security trimming | Platform team leads, DevOps managers |
| `Portal.Maintainer` | Maintainer    | Manage APIs — publish, edit, and curate catalog entries; view scoped analytics                        | API product owners, tech leads       |
| `Portal.User`       | User (Reader) | Read-only — browse the API catalog, use AI chat assistant                                             | All developers                       |

> **Roles are additive.** A user can have more than one role. An admin who also maintains APIs would typically have both `Portal.Admin` and `Portal.Maintainer`.

---

## How RBAC Works

```
┌──────────────┐     login      ┌──────────────┐
│   Frontend   │ ──────────────►│  Entra ID    │
│   (MSAL)     │◄────────────── │  (Azure AD)  │
│              │   JWT with     │              │
│              │   roles claim  │  App Roles:  │
│              │                │  - Portal.*  │
└──────┬───────┘                └──────────────┘
       │ Bearer token
       ▼
┌──────────────┐
│   BFF API    │  1. Validate JWT signature, issuer, audience
│   (FastAPI)  │  2. Extract `roles` claim from token
│              │  3. Route-level check via require_role() / require_any_role()
│              │  4. Return 403 if role is missing
└──────────────┘
```

1. **Frontend (MSAL)**: The user logs in via Microsoft Entra ID. The returned token's `roles` claim contains the App Roles assigned to that user.
2. **Frontend (AuthGuard)**: The `AuthGuard` component reads `user.roles` and can restrict UI sections based on `requiredRoles`.
3. **BFF (JWT Middleware)**: Validates the token and extracts the `roles` array into `request.state.user.roles`.
4. **BFF (RBAC Dependencies)**: `require_role("Portal.Admin")` or `require_any_role(["Portal.User", "Portal.Maintainer"])` enforce access per-route.

There is **no application-level user/role database**. Entra ID is the single source of truth for role assignments.

---

## Entra ID App Role Configuration

### 1. Define App Roles in the App Registration

1. Go to **Azure Portal** → **Microsoft Entra ID** → **App registrations**.
2. Select the **BFF API** app registration (the one that exposes the API scope).
3. Navigate to **App roles** in the left menu.
4. Click **Create app role** for each of the three roles:

   | Display Name | Value               | Allowed Member Types | Description                |
   | ------------ | ------------------- | -------------------- | -------------------------- |
   | Admin        | `Portal.Admin`      | Users/Groups         | Full portal administration |
   | Maintainer   | `Portal.Maintainer` | Users/Groups         | API catalog management     |
   | User         | `Portal.User`       | Users/Groups         | Read-only portal access    |

5. Ensure each role has **Enabled** toggled on.

Alternatively, edit the app manifest JSON directly (App registrations → Manifest):

```json
"appRoles": [
  {
    "allowedMemberTypes": ["User", "Group"],
    "displayName": "Admin",
    "description": "Full portal administration",
    "isEnabled": true,
    "id": "<generate-a-unique-guid>",
    "value": "Portal.Admin"
  },
  {
    "allowedMemberTypes": ["User", "Group"],
    "displayName": "Maintainer",
    "description": "API catalog management",
    "isEnabled": true,
    "id": "<generate-a-unique-guid>",
    "value": "Portal.Maintainer"
  },
  {
    "allowedMemberTypes": ["User", "Group"],
    "displayName": "User",
    "description": "Read-only portal access",
    "isEnabled": true,
    "id": "<generate-a-unique-guid>",
    "value": "Portal.User"
  }
]
```

> **Note:** Each role needs a unique GUID for the `id` field. Generate one with `uuidgen` (macOS/Linux) or `[guid]::NewGuid()` (PowerShell).

### 2. Enable User Assignment

This ensures only users explicitly assigned a role can access the application.

1. Go to **Azure Portal** → **Microsoft Entra ID** → **Enterprise applications**.
2. Find the application corresponding to your BFF API app registration.
3. Under **Properties**, set **Assignment required?** to **Yes**.
4. Click **Save**.

With this enabled, any user who has not been assigned at least one role will be denied access at login time.

### 3. Assign Users or Groups to Roles

1. In the same **Enterprise application**, go to **Users and groups**.
2. Click **Add user/group**.
3. **Select users** — search and select the users or groups.
4. **Select role** — choose from `Admin`, `Maintainer`, or `User`.
5. Click **Assign**.

---

## Group-Based Role Assignment (Recommended)

For organizations with many users, assign roles to **Entra ID security groups** rather than individuals.

### Create Security Groups

| Group Name                   | Role Assignment   | Members                        |
| ---------------------------- | ----------------- | ------------------------------ |
| `sg-apic-portal-admins`      | Portal.Admin      | Platform team leads            |
| `sg-apic-portal-maintainers` | Portal.Maintainer | API product owners, tech leads |
| `sg-apic-portal-users`       | Portal.User       | All developers                 |

### Steps

1. **Create the group**: Azure Portal → Entra ID → Groups → New group.
   - **Group type**: Security
   - **Membership type**: Assigned (or Dynamic if you want auto-membership rules)
2. **Add members**: Go to the group → Members → Add members.
3. **Assign the group to a role**: Enterprise applications → Users and groups → Add user/group → select the group → select the role.

### Dynamic Group Rules (Optional)

For automatic membership, use dynamic group rules based on user attributes:

```
(user.department -eq "Engineering") and (user.jobTitle -contains "Developer")
```

This auto-adds all matching users to the group — and therefore to the associated role.

---

## Local Development Setup

### Prerequisites

- An Azure subscription with an Entra ID tenant
- Permissions to create/manage app registrations (or ask your tenant admin)
- Node.js >= 24, Python 3.14, UV installed

### Step 1 — Create a Dev App Registration

If you don't already have one for local development:

1. Azure Portal → Entra ID → App registrations → New registration.
   - **Name**: `APIC Vibe Portal - Dev`
   - **Supported account types**: Single tenant
   - **Redirect URI**: `http://localhost:3000` (SPA platform)
2. Note the **Application (client) ID** and **Directory (tenant) ID**.
3. Under **Expose an API**, set the Application ID URI (e.g., `api://<client-id>`) and add a scope (e.g., `access_as_user`).

### Step 2 — Add App Roles

Follow the [Define App Roles](#1-define-app-roles-in-the-app-registration) section above to add `Portal.Admin`, `Portal.Maintainer`, and `Portal.User` to this dev registration.

### Step 3 — Assign Yourself to a Role

1. Go to **Enterprise applications** → find your dev app.
2. **Users and groups** → **Add user/group**.
3. Select your user → select the role(s) you need for testing (e.g., `Portal.Admin` for full access).
4. Click **Assign**.

> **Tip:** Assign yourself `Portal.Admin` for development so you can access all routes. Create test users with `Portal.User` or `Portal.Maintainer` to verify role restrictions.

### Step 4 — Configure Environment Variables

Create a `.env.local` file in `src/frontend/`:

```env
NEXT_PUBLIC_MSAL_CLIENT_ID=<your-dev-client-id>
NEXT_PUBLIC_MSAL_AUTHORITY=https://login.microsoftonline.com/<your-tenant-id>
NEXT_PUBLIC_MSAL_REDIRECT_URI=http://localhost:3000
NEXT_PUBLIC_BFF_API_SCOPE=api://<your-client-id>/access_as_user
```

Set environment variables for the BFF (`src/bff/.env` or export in shell):

```env
BFF_ENTRA_TENANT_ID=<your-tenant-id>
BFF_ENTRA_CLIENT_ID=<your-dev-client-id>
BFF_ENTRA_AUDIENCE=api://<your-client-id>
```

### Step 5 — Verify Locally

1. Start the BFF: `cd src/bff && uv run fastapi dev`
2. Start the frontend: `npm run dev --workspace=@apic-vibe-portal/frontend`
3. Open `http://localhost:3000` — you should be redirected to Microsoft login.
4. After login, check the browser dev tools console — the token should contain your assigned roles.
5. Test BFF authorization:

   ```bash
   # Get a token from the browser Network tab (copy the Authorization header value)
   TOKEN="eyJ..."

   # Should succeed (200) if you have Portal.User, Portal.Admin, or Portal.Maintainer
   curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/catalog/

   # Should fail (401) with no token
   curl http://localhost:8000/api/catalog/
   ```

---

## Deployed Environment Setup

For staging and production environments:

1. **Create separate app registrations** per environment (or use the same one with different redirect URIs).
2. **Add the same three App Roles** to each registration.
3. **Assign groups** to roles in the Enterprise application (see [Group-Based Role Assignment](#group-based-role-assignment-recommended)).
4. **Set environment variables** on the Azure Container Apps:
   - Frontend: `NEXT_PUBLIC_MSAL_CLIENT_ID`, `NEXT_PUBLIC_MSAL_AUTHORITY`, `NEXT_PUBLIC_MSAL_REDIRECT_URI`, `NEXT_PUBLIC_BFF_API_SCOPE`
   - BFF: `BFF_ENTRA_TENANT_ID`, `BFF_ENTRA_CLIENT_ID`, `BFF_ENTRA_AUDIENCE`
5. **Enable "Assignment required"** on the Enterprise application to prevent unassigned users from accessing the portal.

---

## Automating with Azure CLI / Microsoft Graph

### List App Roles

```bash
az ad app show --id <app-client-id> --query "appRoles" -o table
```

### Create an App Role via Manifest Update

```bash
# Export current manifest
az ad app show --id <app-client-id> --query "appRoles" -o json > roles.json

# Edit roles.json to add/modify roles, then update
az ad app update --id <app-client-id> --app-roles @roles.json
```

### Assign a User to a Role

```bash
# Get the service principal object ID
SP_ID=$(az ad sp show --id <app-client-id> --query "id" -o tsv)

# Get the role ID (from appRoles array)
ROLE_ID="<portal-user-role-guid>"

# Get the user object ID
USER_OID=$(az ad user show --id user@example.com --query "id" -o tsv)

# Assign the role
az rest --method POST \
  --uri "https://graph.microsoft.com/v1.0/servicePrincipals/$SP_ID/appRoleAssignedTo" \
  --body "{\"principalId\":\"$USER_OID\",\"appRoleId\":\"$ROLE_ID\",\"resourceId\":\"$SP_ID\"}"
```

### Assign a Group to a Role

```bash
GROUP_OID=$(az ad group show --group "sg-apic-portal-users" --query "id" -o tsv)

az rest --method POST \
  --uri "https://graph.microsoft.com/v1.0/servicePrincipals/$SP_ID/appRoleAssignedTo" \
  --body "{\"principalId\":\"$GROUP_OID\",\"appRoleId\":\"$ROLE_ID\",\"resourceId\":\"$SP_ID\"}"
```

### List Current Role Assignments

```bash
az rest --method GET \
  --uri "https://graph.microsoft.com/v1.0/servicePrincipals/$SP_ID/appRoleAssignedTo" \
  -o table
```

---

## Role Hierarchy and Route Protection

### BFF Route Protection Examples

```python
from fastapi import Depends
from apic_vibe_portal_bff.middleware.rbac import require_role, require_any_role

# Any authenticated user with at least one portal role
@router.get("/catalog", dependencies=[Depends(require_any_role(["Portal.User", "Portal.Admin", "Portal.Maintainer"]))])

# Only admins
@router.get("/admin/settings", dependencies=[Depends(require_role("Portal.Admin"))])

# Admins or maintainers
@router.get("/catalog/edit", dependencies=[Depends(require_any_role(["Portal.Admin", "Portal.Maintainer"]))])
```

### Frontend Route Protection Examples

```tsx
// Any authenticated user
<AuthGuard>
  <CatalogPage />
</AuthGuard>

// Admin only
<AuthGuard requiredRoles={['Portal.Admin']}>
  <AdminSettingsPage />
</AuthGuard>

// Admin or Maintainer
<AuthGuard requiredRoles={['Portal.Admin', 'Portal.Maintainer']}>
  <CatalogEditPage />
</AuthGuard>
```

### Current Route → Role Matrix

| Route                      | Required Role(s)                                | Description                |
| -------------------------- | ----------------------------------------------- | -------------------------- |
| `/api/catalog/`            | Portal.User, Portal.Admin, or Portal.Maintainer | Browse API catalog         |
| `/admin/*` (future)        | Portal.Admin                                    | Portal administration      |
| `/catalog/edit/*` (future) | Portal.Admin or Portal.Maintainer               | Catalog management         |
| `/analytics` (future)      | Portal.Admin or Portal.Maintainer               | Analytics dashboard        |
| `/health`, `/docs`         | Public (no auth)                                | Health checks and API docs |

---

## Troubleshooting

### "roles" claim is empty in the token

- **Cause**: The user has not been assigned a role in the Enterprise application.
- **Fix**: Assign the user (or their group) to a role under Enterprise applications → Users and groups.

### 403 Forbidden on a route the user should access

- **Cause**: The token was issued before the role was assigned, or the role value in the token doesn't match what the route expects.
- **Fix**: Log out and log back in to get a fresh token. Verify the role values in the Entra ID app manifest match exactly (`Portal.Admin`, `Portal.Maintainer`, `Portal.User`).

### User can't log in at all (AADSTS50105)

- **Cause**: "Assignment required" is enabled but the user has no role assignment.
- **Fix**: Assign the user to at least one role (typically `Portal.User`).

### Token doesn't include the `roles` claim

- **Cause**: The roles are defined on the wrong app registration, or the frontend is requesting a token for a different audience.
- **Fix**: Ensure App Roles are defined on the BFF API app registration (the one whose audience matches `BFF_ENTRA_AUDIENCE`). Verify `NEXT_PUBLIC_BFF_API_SCOPE` points to the correct app.

### Changes to role assignments aren't reflected

- **Cause**: The user's existing token still has the old roles.
- **Fix**: Role changes take effect on the next token issuance. Have the user log out and back in, or wait for the token to expire and be silently refreshed (typically within 1 hour).
