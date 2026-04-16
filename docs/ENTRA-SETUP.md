# Entra ID Setup Guide — APIC Vibe Portal

Complete walkthrough for configuring Microsoft Entra ID (Azure AD) authentication for the APIC Vibe Portal. This covers **both** app registrations, API scopes, permissions, roles, and environment configuration.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Step 1 — Create the BFF API App Registration](#step-1--create-the-bff-api-app-registration)
  - [1a. Register the application](#1a-register-the-application)
  - [1b. Expose an API (scopes)](#1b-expose-an-api-scopes)
  - [1c. Define App Roles](#1c-define-app-roles)
  - [1d. Configure the Enterprise Application](#1d-configure-the-enterprise-application)
- [Step 2 — Create the Frontend SPA App Registration](#step-2--create-the-frontend-spa-app-registration)
  - [2a. Register the application](#2a-register-the-application)
  - [2b. Add API permissions (scope consent)](#2b-add-api-permissions-scope-consent)
  - [2c. Grant admin consent](#2c-grant-admin-consent)
- [Step 3 — Assign Users to Roles](#step-3--assign-users-to-roles)
- [Step 4 — Configure Environment Variables](#step-4--configure-environment-variables)
  - [Frontend environment variables](#frontend-environment-variables)
  - [BFF environment variables](#bff-environment-variables)
- [Step 5 — Verify the Setup](#step-5--verify-the-setup)
- [How the Pieces Fit Together](#how-the-pieces-fit-together)
- [Azure CLI / Automation](#azure-cli--automation)
  - [Create BFF API app registration](#create-bff-api-app-registration)
  - [Create Frontend SPA app registration](#create-frontend-spa-app-registration)
  - [Add API permissions and grant consent](#add-api-permissions-and-grant-consent)
  - [Add App Roles via manifest](#add-app-roles-via-manifest)
- [Per-Environment Setup](#per-environment-setup)
- [Troubleshooting](#troubleshooting)
- [Related Documentation](#related-documentation)

---

## Architecture Overview

The portal uses a **two-app-registration pattern**, which is the Microsoft-recommended approach for SPA + API architectures:

```
┌──────────────────────┐                     ┌──────────────────────┐
│  Frontend SPA        │                     │  Entra ID            │
│  (Next.js + MSAL)    │                     │  (Azure AD)          │
│                      │  1. Login (PKCE)    │                      │
│  App Registration:   │ ───────────────────►│  Authenticates user  │
│  "APIC Portal - SPA" │◄─────────────────── │  Issues ID + access  │
│                      │  2. Tokens returned │  tokens               │
│  Type: SPA (public)  │     (access token   │                      │
│  No client secret    │      scoped to BFF) │  Access token:       │
│                      │                     │  - aud: BFF API      │
└──────────┬───────────┘                     │  - roles: [Portal.*] │
           │                                 │  - scp: access_as_   │
           │ 3. API call with                │        user           │
           │    Bearer <access_token>        └──────────────────────┘
           │
           ▼
┌──────────────────────┐
│  BFF API             │
│  (FastAPI + PyJWT)   │
│                      │
│  App Registration:   │  4. Validate JWT:
│  "APIC Portal - API" │     - Signature (JWKS)
│                      │     - Issuer (tenant)
│  Type: API           │     - Audience (BFF client ID)
│  Exposes scope:      │     - Expiry
│  access_as_user      │  5. Extract roles claim
│  Defines App Roles   │  6. Enforce RBAC per route
└──────────────────────┘
```

**Key concepts:**

| Concept | Description |
|---|---|
| **Frontend SPA app reg** | A *public client* (no secret). Uses Authorization Code flow with PKCE. Only has redirect URIs. |
| **BFF API app reg** | Exposes an API scope. Defines App Roles (`Portal.Admin`, `Portal.Maintainer`, `Portal.User`). The BFF validates tokens issued for its audience. |
| **Scope** | The frontend requests a token with the BFF's scope (e.g., `api://<bff-client-id>/access_as_user`). This ensures the access token's `aud` claim matches the BFF. |
| **App Roles** | Defined on the BFF API app reg. Assigned to users/groups via the Enterprise Application. Appear in the token's `roles` claim. |

---

## Prerequisites

- An Azure subscription with a Microsoft Entra ID (Azure AD) tenant
- **Application Administrator** or **Cloud Application Administrator** role in the tenant (to create app registrations and grant admin consent)
- Azure Portal access or Azure CLI installed

---

## Step 1 — Create the BFF API App Registration

This app registration represents the backend API. It exposes a scope and defines the RBAC roles.

### 1a. Register the application

1. Go to **Azure Portal** → **Microsoft Entra ID** → **App registrations** → **New registration**.
2. Fill in:
   - **Name**: `APIC Vibe Portal - API` (or your preferred naming, e.g., `apic-portal-api-dev`)
   - **Supported account types**: **Accounts in this organizational directory only** (single tenant)
   - **Redirect URI**: Leave blank (APIs don't need redirect URIs)
3. Click **Register**.
4. Note the **Application (client) ID** — this is the `ENTRA_CLIENT_ID` for the BFF.
5. Note the **Directory (tenant) ID** — this is the `ENTRA_TENANT_ID`.

### 1b. Expose an API (scopes)

This defines the scope that the frontend will request when acquiring an access token.

1. In the BFF API app registration, go to **Expose an API**.
2. Click **Set** next to "Application ID URI". Accept the default (`api://<client-id>`) or set a custom URI.
3. Click **Add a scope**:

   | Field | Value |
   |---|---|
   | **Scope name** | `access_as_user` |
   | **Who can consent** | Admins and users |
   | **Admin consent display name** | Access APIC Vibe Portal API |
   | **Admin consent description** | Allows the APIC Vibe Portal frontend to call the BFF API on behalf of the signed-in user. |
   | **User consent display name** | Access APIC Vibe Portal |
   | **User consent description** | Allow the portal to access the API on your behalf. |
   | **State** | Enabled |

4. Click **Add scope**. The full scope URI will be: `api://<bff-client-id>/access_as_user`

> **This scope value is what you'll set as `NEXT_PUBLIC_BFF_API_SCOPE` in the frontend.**

### 1c. Define App Roles

App Roles control what users can do in the portal. These are returned in the `roles` claim of the access token.

1. In the BFF API app registration, go to **App roles**.
2. Click **Create app role** for each role:

   | Display Name | Value | Allowed Member Types | Description |
   |---|---|---|---|
   | Admin | `Portal.Admin` | Users/Groups | Full portal administration |
   | Maintainer | `Portal.Maintainer` | Users/Groups | API catalog management |
   | User | `Portal.User` | Users/Groups | Read-only portal access |

3. Ensure each role is **Enabled**.

**Alternative — edit the manifest directly** (App registrations → Manifest):

```json
"appRoles": [
  {
    "allowedMemberTypes": ["User", "Group"],
    "displayName": "Admin",
    "description": "Full portal administration",
    "isEnabled": true,
    "id": "GENERATE-UNIQUE-GUID-1",
    "value": "Portal.Admin"
  },
  {
    "allowedMemberTypes": ["User", "Group"],
    "displayName": "Maintainer",
    "description": "API catalog management",
    "isEnabled": true,
    "id": "GENERATE-UNIQUE-GUID-2",
    "value": "Portal.Maintainer"
  },
  {
    "allowedMemberTypes": ["User", "Group"],
    "displayName": "User",
    "description": "Read-only portal access",
    "isEnabled": true,
    "id": "GENERATE-UNIQUE-GUID-3",
    "value": "Portal.User"
  }
]
```

> Generate GUIDs with `uuidgen` (macOS/Linux) or `[guid]::NewGuid()` (PowerShell).

### 1d. Configure the Enterprise Application

1. Go to **Azure Portal** → **Microsoft Entra ID** → **Enterprise applications**.
2. Find the application corresponding to the BFF API app registration (same name).
3. Under **Properties**:
   - Set **Assignment required?** to **Yes** — only users with an assigned role can obtain tokens.
4. Click **Save**.

---

## Step 2 — Create the Frontend SPA App Registration

This app registration represents the browser-based frontend. It is a **public client** (no secret needed).

### 2a. Register the application

1. Go to **Azure Portal** → **Microsoft Entra ID** → **App registrations** → **New registration**.
2. Fill in:
   - **Name**: `APIC Vibe Portal - SPA` (or `apic-portal-spa-dev`)
   - **Supported account types**: **Accounts in this organizational directory only** (single tenant)
   - **Redirect URI**:
     - **Platform**: Single-page application (SPA)
     - **URI**: `http://localhost:3000` (for local dev; add deployed URLs later)
3. Click **Register**.
4. Note the **Application (client) ID** — this is the `NEXT_PUBLIC_MSAL_CLIENT_ID`.

> **Important:** Select **Single-page application** as the platform type. This enables the Authorization Code flow with PKCE, which is the secure flow for browser apps. Do **not** select "Web" or enable implicit grant.

#### Add additional redirect URIs (for deployed environments)

1. In the SPA app registration, go to **Authentication**.
2. Under **Single-page application** → **Redirect URIs**, add:
   - `https://your-staging-url.azurecontainerapps.io`
   - `https://your-production-url.azurecontainerapps.io`
   - `https://your-custom-domain.com` (if applicable)
3. Click **Save**.

### 2b. Add API permissions (scope consent)

This grants the frontend permission to request the BFF API's scope.

1. In the SPA app registration, go to **API permissions**.
2. Click **Add a permission** → **My APIs**.
3. Select the **APIC Vibe Portal - API** (BFF) app registration.
4. Select **Delegated permissions**.
5. Check **access_as_user**.
6. Click **Add permissions**.

You should now see the permission listed as:

```
API / Permission Name                              Type        Status
APIC Vibe Portal - API / access_as_user           Delegated   Not granted
```

### 2c. Grant admin consent

If you have admin privileges:

1. Still on the **API permissions** page of the SPA app registration.
2. Click **Grant admin consent for \<tenant name\>**.
3. Click **Yes** to confirm.

The status column should change to **Granted for \<tenant name\>**.

> **If you don't have admin privileges:** Ask your tenant administrator to grant consent. Without consent, users will see a consent prompt on first login (if user consent is allowed in the tenant) or will be blocked entirely.

---

## Step 3 — Assign Users to Roles

Users must be assigned to at least one App Role to access the portal (when "Assignment required" is enabled).

1. Go to **Azure Portal** → **Microsoft Entra ID** → **Enterprise applications**.
2. Find the **BFF API** enterprise application (APIC Vibe Portal - API).
3. Go to **Users and groups** → **Add user/group**.
4. **Select users**: Search and select the user(s) or group(s).
5. **Select role**: Choose `Admin`, `Maintainer`, or `User`.
6. Click **Assign**.

> For group-based assignment (recommended for larger teams), see the [RBAC Setup Guide](RBAC-SETUP.md#group-based-role-assignment-recommended).

---

## Step 4 — Configure Environment Variables

### Frontend environment variables

Create `src/frontend/.env.local`:

```env
# The SPA app registration's Application (client) ID
NEXT_PUBLIC_MSAL_CLIENT_ID=<spa-client-id>

# Entra ID authority URL for your tenant
NEXT_PUBLIC_MSAL_AUTHORITY=https://login.microsoftonline.com/<tenant-id>

# Where Entra ID redirects after login
NEXT_PUBLIC_MSAL_REDIRECT_URI=http://localhost:3000

# The BFF API's exposed scope (from Step 1b)
NEXT_PUBLIC_BFF_API_SCOPE=api://<bff-client-id>/access_as_user
```

| Variable | Source |
|---|---|
| `NEXT_PUBLIC_MSAL_CLIENT_ID` | SPA app registration → Application (client) ID |
| `NEXT_PUBLIC_MSAL_AUTHORITY` | `https://login.microsoftonline.com/<tenant-id>` |
| `NEXT_PUBLIC_MSAL_REDIRECT_URI` | Must match a redirect URI in the SPA app registration |
| `NEXT_PUBLIC_BFF_API_SCOPE` | BFF API app registration → Expose an API → scope URI |

### BFF environment variables

Set in `src/bff/.env` or export in your shell:

```env
# Your Entra ID tenant ID
ENTRA_TENANT_ID=<tenant-id>

# The BFF API app registration's Application (client) ID
ENTRA_CLIENT_ID=<bff-client-id>

# The audience the BFF expects in incoming tokens (usually same as client ID or Application ID URI)
ENTRA_AUDIENCE=api://<bff-client-id>
```

| Variable | Source |
|---|---|
| `ENTRA_TENANT_ID` | Entra ID → Overview → Tenant ID |
| `ENTRA_CLIENT_ID` | BFF API app registration → Application (client) ID |
| `ENTRA_AUDIENCE` | BFF API app registration → Application ID URI (e.g., `api://<bff-client-id>`) |

> **Note on `ENTRA_AUDIENCE`**: This must match the `aud` claim in the access token. When the frontend requests a token with scope `api://<bff-client-id>/access_as_user`, the resulting token's `aud` will be `api://<bff-client-id>`. Set `ENTRA_AUDIENCE` to match.

---

## Step 5 — Verify the Setup

### Start the services

```bash
# Terminal 1 — BFF
cd src/bff
uv run fastapi dev

# Terminal 2 — Frontend
npm run dev --workspace=@apic-vibe-portal/frontend
```

### Verify authentication

1. Open `http://localhost:3000` in your browser.
2. You should be redirected to the Microsoft login page.
3. Sign in with a user who has been assigned a role.
4. After successful login, the frontend should display the user's name in the header.

### Verify token contents

1. Open browser DevTools → **Network** tab.
2. Find a request to the BFF API (e.g., `/api/catalog/`).
3. Copy the `Authorization: Bearer <token>` header value.
4. Decode the token at [jwt.ms](https://jwt.ms) and verify:
   - `aud` matches your BFF API's Application ID URI
   - `iss` matches `https://login.microsoftonline.com/<tenant-id>/v2.0`
   - `roles` contains your assigned role(s) (e.g., `["Portal.Admin"]`)
   - `scp` contains `access_as_user`

### Verify RBAC

```bash
TOKEN="<paste-bearer-token-here>"

# Should return 200 (requires Portal.User, Portal.Admin, or Portal.Maintainer)
curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/catalog/

# Should return 401 (no token)
curl -s -o /dev/null -w "%{http_code}" \
  http://localhost:8000/api/catalog/

# Public endpoints (no auth required)
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs
```

---

## How the Pieces Fit Together

Here's a quick reference showing how the two app registrations connect:

```
Frontend SPA App Reg                    BFF API App Reg
─────────────────────                   ─────────────────────
Client ID: <spa-id>                     Client ID: <bff-id>
Type: SPA (public)                      Type: API
Redirect: http://localhost:3000         Application ID URI: api://<bff-id>
                                        
API Permissions:                        Exposed Scopes:
  └─ APIC Portal API /                   └─ access_as_user
     access_as_user (Delegated)         
                                        App Roles:
                                          ├─ Portal.Admin
                                          ├─ Portal.Maintainer
                                          └─ Portal.User

                    Token Flow
                    ──────────
1. Frontend calls MSAL.acquireTokenSilent({ scopes: ["api://<bff-id>/access_as_user"] })
2. Entra ID issues an access token with:
   - aud: api://<bff-id>              ← matches ENTRA_AUDIENCE
   - roles: ["Portal.User"]           ← from App Role assignment
   - scp: "access_as_user"            ← from API permission
3. Frontend sends: Authorization: Bearer <access_token>
4. BFF validates: signature, issuer, audience, expiry
5. BFF extracts roles from token → enforces RBAC per route
```

---

## Azure CLI / Automation

For scripted/automated setup (CI/CD, infrastructure-as-code):

### Create BFF API app registration

```bash
# Create the app registration
BFF_APP=$(az ad app create \
  --display-name "APIC Vibe Portal - API" \
  --sign-in-audience AzureADMyOrg \
  --query "{appId: appId, id: id}" \
  -o json)

BFF_CLIENT_ID=$(echo $BFF_APP | jq -r '.appId')
BFF_OBJECT_ID=$(echo $BFF_APP | jq -r '.id')

echo "BFF Client ID: $BFF_CLIENT_ID"

# Set the Application ID URI
az ad app update --id $BFF_CLIENT_ID \
  --identifier-uris "api://$BFF_CLIENT_ID"

# Add the access_as_user scope
# First, get the current API settings and add the scope
SCOPE_ID=$(uuidgen)
az ad app update --id $BFF_CLIENT_ID \
  --set api="{\"oauth2PermissionScopes\":[{\"id\":\"$SCOPE_ID\",\"adminConsentDescription\":\"Allows the APIC Vibe Portal frontend to call the BFF API on behalf of the signed-in user.\",\"adminConsentDisplayName\":\"Access APIC Vibe Portal API\",\"isEnabled\":true,\"type\":\"User\",\"userConsentDescription\":\"Allow the portal to access the API on your behalf.\",\"userConsentDisplayName\":\"Access APIC Vibe Portal\",\"value\":\"access_as_user\"}]}"

# Create the service principal (Enterprise Application)
az ad sp create --id $BFF_CLIENT_ID

# Enable "assignment required"
SP_ID=$(az ad sp show --id $BFF_CLIENT_ID --query "id" -o tsv)
az rest --method PATCH \
  --uri "https://graph.microsoft.com/v1.0/servicePrincipals/$SP_ID" \
  --body '{"appRoleAssignmentRequired": true}'
```

### Create Frontend SPA app registration

```bash
# Create the app registration with SPA redirect URI
SPA_APP=$(az ad app create \
  --display-name "APIC Vibe Portal - SPA" \
  --sign-in-audience AzureADMyOrg \
  --web-redirect-uris "" \
  --query "{appId: appId, id: id}" \
  -o json)

SPA_CLIENT_ID=$(echo $SPA_APP | jq -r '.appId')
SPA_OBJECT_ID=$(echo $SPA_APP | jq -r '.id')

echo "SPA Client ID: $SPA_CLIENT_ID"

# Add SPA platform redirect URI
az rest --method PATCH \
  --uri "https://graph.microsoft.com/v1.0/applications/$SPA_OBJECT_ID" \
  --body "{\"spa\":{\"redirectUris\":[\"http://localhost:3000\"]}}"

# Create the service principal
az ad sp create --id $SPA_CLIENT_ID
```

### Add API permissions and grant consent

```bash
# Get the BFF service principal ID and scope ID
BFF_SP_ID=$(az ad sp show --id $BFF_CLIENT_ID --query "id" -o tsv)

# Add delegated permission for access_as_user scope
az ad app permission add \
  --id $SPA_CLIENT_ID \
  --api $BFF_CLIENT_ID \
  --api-permissions "$SCOPE_ID=Scope"

# Grant admin consent
az ad app permission admin-consent --id $SPA_CLIENT_ID
```

### Add App Roles via manifest

```bash
ADMIN_ROLE_ID=$(uuidgen)
MAINTAINER_ROLE_ID=$(uuidgen)
USER_ROLE_ID=$(uuidgen)

az ad app update --id $BFF_CLIENT_ID --app-roles "[
  {\"allowedMemberTypes\":[\"User\",\"Group\"],\"displayName\":\"Admin\",\"description\":\"Full portal administration\",\"isEnabled\":true,\"id\":\"$ADMIN_ROLE_ID\",\"value\":\"Portal.Admin\"},
  {\"allowedMemberTypes\":[\"User\",\"Group\"],\"displayName\":\"Maintainer\",\"description\":\"API catalog management\",\"isEnabled\":true,\"id\":\"$MAINTAINER_ROLE_ID\",\"value\":\"Portal.Maintainer\"},
  {\"allowedMemberTypes\":[\"User\",\"Group\"],\"displayName\":\"User\",\"description\":\"Read-only portal access\",\"isEnabled\":true,\"id\":\"$USER_ROLE_ID\",\"value\":\"Portal.User\"}
]"
```

### Assign a user to a role

```bash
USER_OID=$(az ad user show --id user@example.com --query "id" -o tsv)

az rest --method POST \
  --uri "https://graph.microsoft.com/v1.0/servicePrincipals/$BFF_SP_ID/appRoleAssignedTo" \
  --body "{\"principalId\":\"$USER_OID\",\"appRoleId\":\"$USER_ROLE_ID\",\"resourceId\":\"$BFF_SP_ID\"}"
```

---

## Per-Environment Setup

For each environment (dev, staging, production), you can either:

**Option A — Separate app registrations per environment** (recommended for isolation):

| Environment | BFF API App Reg | SPA App Reg | Redirect URIs |
|---|---|---|---|
| Dev (local) | `apic-portal-api-dev` | `apic-portal-spa-dev` | `http://localhost:3000` |
| Staging | `apic-portal-api-stg` | `apic-portal-spa-stg` | `https://stg.yourportal.com` |
| Production | `apic-portal-api-prd` | `apic-portal-spa-prd` | `https://yourportal.com` |

**Option B — Single app registration with multiple redirect URIs** (simpler for small teams):

- One BFF API app reg and one SPA app reg
- Add all redirect URIs (localhost, staging, prod) to the SPA app reg
- Use the same client IDs across environments
- Roles and scopes are shared

For either option, set the environment variables appropriately per deployment.

On **Azure Container Apps**, set environment variables using:

```bash
# Frontend container
az containerapp update \
  --name apic-portal-frontend \
  --resource-group <rg-name> \
  --set-env-vars \
    NEXT_PUBLIC_MSAL_CLIENT_ID=<spa-client-id> \
    NEXT_PUBLIC_MSAL_AUTHORITY=https://login.microsoftonline.com/<tenant-id> \
    NEXT_PUBLIC_MSAL_REDIRECT_URI=https://your-deployed-url \
    NEXT_PUBLIC_BFF_API_SCOPE=api://<bff-client-id>/access_as_user

# BFF container
az containerapp update \
  --name apic-portal-bff \
  --resource-group <rg-name> \
  --set-env-vars \
    ENTRA_TENANT_ID=<tenant-id> \
    ENTRA_CLIENT_ID=<bff-client-id> \
    ENTRA_AUDIENCE=api://<bff-client-id>
```

---

## Troubleshooting

### Token `aud` claim doesn't match BFF expectations

**Symptom**: BFF returns 401 with "Invalid token", token decodes with wrong `aud`.

**Cause**: The frontend is requesting a token for the wrong scope, or `ENTRA_AUDIENCE` doesn't match.

**Fix**: Ensure `NEXT_PUBLIC_BFF_API_SCOPE` is set to `api://<bff-client-id>/access_as_user` and `ENTRA_AUDIENCE` is set to `api://<bff-client-id>`.

### "AADSTS65001: The user or administrator has not consented"

**Symptom**: Login fails with a consent error.

**Cause**: The SPA app registration hasn't been granted permission to the BFF API's scope.

**Fix**: Go to the SPA app registration → API permissions → Grant admin consent. Or follow [Step 2c](#2c-grant-admin-consent).

### "AADSTS50105: The signed in user is not assigned to a role"

**Symptom**: Login fails because "Assignment required" is enabled but the user has no role.

**Fix**: Assign the user to at least one role in the BFF API's Enterprise Application → Users and groups.

### `roles` claim is empty or missing in the token

**Cause**: The user hasn't been assigned a role, or roles are defined on the wrong app registration.

**Fix**: 
1. Verify App Roles are defined on the **BFF API** app registration (not the SPA).
2. Assign the user to a role via the BFF API's **Enterprise Application** → Users and groups.
3. Log out and log back in to get a fresh token.

### Token contains `scp` but no `roles`

**Cause**: This is normal if no roles are assigned yet. The `scp` claim comes from the delegated permission (scope), and `roles` comes from App Role assignments. They are independent.

**Fix**: Assign the user to a role (see Step 3).

### Frontend login works but BFF returns 401

**Cause**: Multiple possible causes:
1. Token audience mismatch (check `aud` claim vs `ENTRA_AUDIENCE`)
2. Token issuer mismatch (check tenant ID)
3. BFF env vars not set

**Fix**: Decode the token at [jwt.ms](https://jwt.ms) and compare claims against BFF environment variables.

### MSAL "interaction_required" error

**Symptom**: Silent token acquisition fails, MSAL throws `InteractionRequiredAuthError`.

**Cause**: The user needs to re-authenticate (consent changed, MFA required, session expired).

**Fix**: The MSAL integration handles this automatically by falling back to interactive login. If it persists, clear the browser's session storage and try again.

### "redirect_uri mismatch" error during login

**Symptom**: Entra ID returns an error about redirect URI not matching.

**Cause**: `NEXT_PUBLIC_MSAL_REDIRECT_URI` doesn't match any redirect URI registered in the SPA app registration.

**Fix**: Ensure the redirect URI in `.env.local` exactly matches one of the URIs in the SPA app registration → Authentication → Single-page application → Redirect URIs (including protocol, host, port, and path).

---

## Related Documentation

- [RBAC Setup Guide](RBAC-SETUP.md) — Detailed guide for role assignments, group-based RBAC, and role troubleshooting
- [Architecture Document](project/apic_architecture.md) — System architecture and security model
- [Task 008 — Entra ID Authentication](project/plan/008-entra-id-authentication.md) — Implementation plan for auth integration
- [Microsoft: Register an application with the Microsoft identity platform](https://learn.microsoft.com/entra/identity-platform/quickstart-register-app)
- [Microsoft: Protected web API — App registration](https://learn.microsoft.com/entra/identity-platform/scenario-protected-web-api-app-registration)
- [Microsoft: SPA that calls web APIs — App registration](https://learn.microsoft.com/entra/identity-platform/scenario-spa-app-registration)
- [Microsoft: Add app roles and get them from a token](https://learn.microsoft.com/entra/identity-platform/howto-add-app-roles-in-apps)
