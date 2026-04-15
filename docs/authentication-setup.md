# Entra ID Authentication Setup Guide

This document provides step-by-step instructions for setting up Microsoft Entra ID (Azure AD) authentication for the APIC Vibe Portal, including app registrations, environment variable configuration, GitHub secrets for CI/CD, and Container Apps deployment-time configuration.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Step 1: Create the BFF API App Registration](#step-1-create-the-bff-api-app-registration)
- [Step 2: Create the Frontend SPA App Registration](#step-2-create-the-frontend-spa-app-registration)
- [Step 3: Configure App Roles](#step-3-configure-app-roles)
- [Step 4: Assign Users to Roles](#step-4-assign-users-to-roles)
- [Step 5: Configure Local Development](#step-5-configure-local-development)
- [Step 6: Configure GitHub Secrets for CI/CD](#step-6-configure-github-secrets-for-cicd)
- [Step 7: Container Apps Deployment](#step-7-container-apps-deployment)
- [Environment Variable Reference](#environment-variable-reference)
- [Troubleshooting](#troubleshooting)

## Architecture Overview

The portal uses a two-app-registration pattern:

```
┌──────────────────┐     Bearer Token     ┌──────────────────┐
│  Frontend SPA    │ ──────────────────►   │  BFF API         │
│  (MSAL React)    │                       │  (FastAPI)       │
│                  │                       │                  │
│  Public client   │                       │  Confidential    │
│  Auth Code +PKCE │                       │  JWT validation  │
│                  │                       │  via JWKS        │
└──────────────────┘                       └──────────────────┘
        │                                          │
        │  Redirect login                          │  Validates:
        ▼                                          │  - Signature (JWKS)
┌──────────────────┐                               │  - Issuer
│  Entra ID        │                               │  - Audience
│  (Azure AD)      │                               │  - Expiration
│                  │◄──────────────────────────────-┘  - Roles
│  Tenant          │
└──────────────────┘
```

- **Frontend SPA App Registration**: Public client using Authorization Code flow with PKCE (via MSAL). No client secret needed.
- **BFF API App Registration**: Exposes an API scope that the frontend requests tokens for. The BFF validates tokens using JWKS (no client secret needed for validation).

## Prerequisites

- Azure CLI (`az`) version 2.50.0+
- An Azure subscription with Entra ID (Azure AD) tenant
- Permissions to create app registrations in your tenant (Application Administrator or Global Administrator role)
- The GitHub repository configured with CI/CD (see [CI/CD Setup Guide](CI_CD_SETUP.md))

## Step 1: Create the BFF API App Registration

This app registration represents the BFF API. The frontend will request tokens scoped to this API.

```bash
# Login to Azure
az login

# Set variables
TENANT_ID=$(az account show --query tenantId -o tsv)
BFF_APP_NAME="apic-vibe-portal-bff-api"

# Create the BFF API app registration
BFF_APP_ID=$(az ad app create \
  --display-name "$BFF_APP_NAME" \
  --sign-in-audience "AzureADMyOrg" \
  --query appId -o tsv)

echo "BFF App (Client) ID: $BFF_APP_ID"

# Set the Application ID URI (used as the audience)
az ad app update \
  --id "$BFF_APP_ID" \
  --identifier-uris "api://$BFF_APP_ID"

# Expose an API scope that the frontend will request
# Generate a UUID for the scope ID
SCOPE_ID=$(python3 -c "import uuid; print(uuid.uuid4())")

az ad app update \
  --id "$BFF_APP_ID" \
  --set "api.oauth2PermissionScopes=[{
    \"adminConsentDescription\": \"Access APIC Vibe Portal BFF API\",
    \"adminConsentDisplayName\": \"Access BFF API\",
    \"id\": \"$SCOPE_ID\",
    \"isEnabled\": true,
    \"type\": \"User\",
    \"userConsentDescription\": \"Access the APIC Vibe Portal API on your behalf\",
    \"userConsentDisplayName\": \"Access BFF API\",
    \"value\": \"access_as_user\"
  }]"

echo ""
echo "=== BFF API App Registration ==="
echo "App Name:          $BFF_APP_NAME"
echo "App (Client) ID:   $BFF_APP_ID"
echo "Tenant ID:         $TENANT_ID"
echo "Audience:          api://$BFF_APP_ID"
echo "Scope:             api://$BFF_APP_ID/access_as_user"
echo "================================="
```

> **Save these values** — you'll need them for configuring the frontend, BFF, and GitHub secrets.

## Step 2: Create the Frontend SPA App Registration

This app registration is for the Next.js frontend SPA. It uses MSAL with Authorization Code flow + PKCE.

```bash
# Set variables
FRONTEND_APP_NAME="apic-vibe-portal-frontend"

# Determine redirect URIs for each environment
# Local dev:    http://localhost:3000
# Dev:          https://<frontend-app>.azurecontainerapps.io
# Staging:      https://<frontend-app>.azurecontainerapps.io
# Prod:         https://your-custom-domain.com

# Create the Frontend SPA app registration
FRONTEND_APP_ID=$(az ad app create \
  --display-name "$FRONTEND_APP_NAME" \
  --sign-in-audience "AzureADMyOrg" \
  --web-redirect-uris "" \
  --query appId -o tsv)

echo "Frontend App (Client) ID: $FRONTEND_APP_ID"

# Configure SPA redirect URIs (not web redirect URIs!)
# This enables Authorization Code flow with PKCE
az ad app update \
  --id "$FRONTEND_APP_ID" \
  --set "spa.redirectUris=['http://localhost:3000']"

# Grant the frontend app permission to access the BFF API scope
BFF_API_RESOURCE_ID=$(az ad app show --id "$BFF_APP_ID" --query id -o tsv)

az ad app permission add \
  --id "$FRONTEND_APP_ID" \
  --api "$BFF_APP_ID" \
  --api-permissions "$SCOPE_ID=Scope"

# Grant admin consent for the API permission
az ad app permission admin-consent --id "$FRONTEND_APP_ID"

echo ""
echo "=== Frontend SPA App Registration ==="
echo "App Name:          $FRONTEND_APP_NAME"
echo "App (Client) ID:   $FRONTEND_APP_ID"
echo "Tenant ID:         $TENANT_ID"
echo "Authority:         https://login.microsoftonline.com/$TENANT_ID"
echo "Redirect URI:      http://localhost:3000 (add more per environment)"
echo "BFF API Scope:     api://$BFF_APP_ID/access_as_user"
echo "======================================"
```

### Add Redirect URIs for Deployed Environments

After deploying Container Apps, add the deployed frontend URLs as redirect URIs:

```bash
# Get the frontend URL from Container Apps
FRONTEND_URL=$(az containerapp show \
  --name <frontend-app-name> \
  --resource-group <resource-group> \
  --query properties.configuration.ingress.fqdn -o tsv)

# Update SPA redirect URIs to include all environments
az ad app update \
  --id "$FRONTEND_APP_ID" \
  --set "spa.redirectUris=[
    'http://localhost:3000',
    'https://$FRONTEND_URL'
  ]"
```

## Step 3: Configure App Roles

Define application roles for RBAC. These are set on the **BFF API** app registration.

```bash
az ad app update \
  --id "$BFF_APP_ID" \
  --app-roles '[
    {
      "allowedMemberTypes": ["User"],
      "description": "Standard portal users who can browse APIs and use the AI assistant",
      "displayName": "Portal User",
      "isEnabled": true,
      "value": "Portal.User",
      "id": "'$(python3 -c "import uuid; print(uuid.uuid4())")'"
    },
    {
      "allowedMemberTypes": ["User"],
      "description": "Administrators with full access to portal management",
      "displayName": "Portal Admin",
      "isEnabled": true,
      "value": "Portal.Admin",
      "id": "'$(python3 -c "import uuid; print(uuid.uuid4())")'"
    },
    {
      "allowedMemberTypes": ["User"],
      "description": "API owners who can manage their API listings and governance",
      "displayName": "API Owner",
      "isEnabled": true,
      "value": "API.Owner",
      "id": "'$(python3 -c "import uuid; print(uuid.uuid4())")'"
    }
  ]'
```

## Step 4: Assign Users to Roles

Assign users (or groups) to the app roles via Azure Portal or CLI:

### Via Azure Portal

1. Go to **Entra ID** > **Enterprise Applications**
2. Find the BFF API app (`apic-vibe-portal-bff-api`)
3. Go to **Users and groups** > **Add user/group**
4. Select the user/group and assign the appropriate role

### Via Azure CLI

```bash
# Get the service principal (enterprise app) object ID
BFF_SP_ID=$(az ad sp show --id "$BFF_APP_ID" --query id -o tsv)

# Get the user's object ID
USER_OID=$(az ad user show --id "user@yourtenant.onmicrosoft.com" --query id -o tsv)

# Get the role ID (Portal.User in this example)
ROLE_ID=$(az ad app show --id "$BFF_APP_ID" \
  --query "appRoles[?value=='Portal.User'].id" -o tsv)

# Assign the role
az rest --method POST \
  --uri "https://graph.microsoft.com/v1.0/servicePrincipals/$BFF_SP_ID/appRoleAssignments" \
  --body "{
    \"principalId\": \"$USER_OID\",
    \"appRoleId\": \"$ROLE_ID\",
    \"resourceId\": \"$BFF_SP_ID\"
  }"
```

## Step 5: Configure Local Development

### Frontend (`.env.local`)

Create `src/frontend/.env.local` (this file is gitignored):

```env
# Entra ID Authentication
NEXT_PUBLIC_MSAL_CLIENT_ID=<frontend-app-client-id>
NEXT_PUBLIC_MSAL_AUTHORITY=https://login.microsoftonline.com/<tenant-id>
NEXT_PUBLIC_MSAL_REDIRECT_URI=http://localhost:3000
NEXT_PUBLIC_BFF_API_SCOPE=api://<bff-app-client-id>/access_as_user

# BFF API URL
NEXT_PUBLIC_BFF_URL=http://localhost:8000
```

### BFF (`.env`)

Create `src/bff/.env` (this file is gitignored):

```env
# Entra ID Authentication
ENTRA_TENANT_ID=<tenant-id>
ENTRA_CLIENT_ID=<bff-app-client-id>
ENTRA_AUDIENCE=api://<bff-app-client-id>

# Leave ENTRA_TENANT_ID empty to disable auth in local dev:
# ENTRA_TENANT_ID=
```

> **Tip**: To develop without Entra ID locally, leave `ENTRA_TENANT_ID` empty. The auth middleware will pass all requests through without validation.

## Step 6: Configure GitHub Secrets for CI/CD

Add the following secrets to your GitHub repository (**Settings** > **Secrets and variables** > **Actions**):

### Authentication Secrets (per environment)

These secrets are used by the deploy script to set env vars on the Container Apps at deploy time.

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `ENTRA_TENANT_ID` | `<tenant-id>` | Entra ID tenant ID (same for all environments) |
| `ENTRA_BFF_CLIENT_ID` | `<bff-app-client-id>` | BFF API app registration client ID |
| `ENTRA_BFF_AUDIENCE` | `api://<bff-app-client-id>` | BFF API audience (Application ID URI) |
| `MSAL_CLIENT_ID` | `<frontend-app-client-id>` | Frontend SPA app registration client ID |
| `BFF_API_SCOPE` | `api://<bff-app-client-id>/access_as_user` | BFF API scope for token requests |

> **Note**: These are **not** sensitive secrets (they are client IDs and public identifiers). However, storing them as GitHub secrets keeps the configuration centralized and environment-specific.

### Existing CI/CD Secrets (already configured)

These should already be set up per the [CI/CD Setup Guide](CI_CD_SETUP.md):

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `AZURE_CLIENT_ID` | `<github-actions-app-id>` | GitHub Actions OIDC app client ID |
| `AZURE_TENANT_ID` | `<tenant-id>` | Azure tenant ID |
| `AZURE_SUBSCRIPTION_ID` | `<subscription-id>` | Azure subscription ID |
| `AZURE_RESOURCE_GROUP_DEV` | `rg-apic-vibe-portal-dev` | Dev resource group name |
| `AZURE_RESOURCE_GROUP_STAGING` | `rg-apic-vibe-portal-staging` | Staging resource group |
| `AZURE_RESOURCE_GROUP_PROD` | `rg-apic-vibe-portal-prod` | Prod resource group |

## Step 7: Container Apps Deployment

Auth environment variables are injected into the Container Apps at deploy time via the `scripts/deploy-container-apps.sh` script. The CI/CD workflow passes the auth secrets as arguments to the deploy script.

### How It Works

1. **Build time** (frontend): `NEXT_PUBLIC_*` env vars are baked into the Next.js build via Docker build args
2. **Deploy time** (BFF): `ENTRA_*` env vars are set as Container App environment variables via `--set-env-vars`

### Frontend (Build-time Environment Variables)

The frontend `NEXT_PUBLIC_*` variables must be available at **build time** because Next.js inlines them into the client bundle. The deploy workflow passes them as Docker build args:

```bash
docker build \
  --build-arg NEXT_PUBLIC_MSAL_CLIENT_ID=$MSAL_CLIENT_ID \
  --build-arg NEXT_PUBLIC_MSAL_AUTHORITY=https://login.microsoftonline.com/$ENTRA_TENANT_ID \
  --build-arg NEXT_PUBLIC_MSAL_REDIRECT_URI=https://$FRONTEND_FQDN \
  --build-arg NEXT_PUBLIC_BFF_API_SCOPE=$BFF_API_SCOPE \
  --build-arg NEXT_PUBLIC_BFF_URL=https://$BFF_FQDN \
  -t $IMAGE .
```

### BFF (Deploy-time Environment Variables)

The BFF reads env vars at runtime, so they are set on the Container App at deploy time:

```bash
az containerapp update \
  --name $BFF_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --set-env-vars \
    ENTRA_TENANT_ID=$ENTRA_TENANT_ID \
    ENTRA_CLIENT_ID=$ENTRA_BFF_CLIENT_ID \
    ENTRA_AUDIENCE=$ENTRA_BFF_AUDIENCE
```

## Environment Variable Reference

### Frontend Environment Variables

| Variable | Required | Description | Set At |
|----------|----------|-------------|--------|
| `NEXT_PUBLIC_MSAL_CLIENT_ID` | Yes | Frontend SPA app client ID | Build time |
| `NEXT_PUBLIC_MSAL_AUTHORITY` | Yes | `https://login.microsoftonline.com/<tenant-id>` | Build time |
| `NEXT_PUBLIC_MSAL_REDIRECT_URI` | Yes | Frontend URL (e.g., `https://frontend.azurecontainerapps.io`) | Build time |
| `NEXT_PUBLIC_BFF_API_SCOPE` | Yes | `api://<bff-client-id>/access_as_user` | Build time |
| `NEXT_PUBLIC_BFF_URL` | Yes | BFF API URL (e.g., `https://bff.azurecontainerapps.io`) | Build time |

### BFF Environment Variables

| Variable | Required | Description | Set At |
|----------|----------|-------------|--------|
| `ENTRA_TENANT_ID` | Yes* | Entra ID tenant ID | Deploy time |
| `ENTRA_CLIENT_ID` | Yes* | BFF API app client ID | Deploy time |
| `ENTRA_AUDIENCE` | Yes* | Expected token audience (`api://<bff-client-id>`) | Deploy time |

> *Required in production. If `ENTRA_TENANT_ID` is empty, auth middleware passes all requests through (local dev mode).

## Troubleshooting

### "Invalid token audience" Error (BFF)

- Verify `ENTRA_AUDIENCE` matches the Application ID URI on the BFF app registration
- Check that the frontend is requesting tokens for the correct scope (`NEXT_PUBLIC_BFF_API_SCOPE`)

### "AADSTS65001: The user or administrator has not consented" Error

- Run admin consent: `az ad app permission admin-consent --id <frontend-app-id>`

### Login Redirect Fails / Loops

- Verify the redirect URI in the SPA app registration matches `NEXT_PUBLIC_MSAL_REDIRECT_URI` exactly
- Ensure the redirect URI is configured as a **SPA** redirect (not Web)

### User Has No Roles

- Assign the user to an app role (see [Step 4](#step-4-assign-users-to-roles))
- After role assignment, the user must sign out and sign back in for the new roles to appear in the token

### Token Not Sent to BFF

- Check browser Network tab for the `Authorization` header on API requests
- Ensure `setTokenProvider` is called during app initialization
- Verify the `NEXT_PUBLIC_BFF_API_SCOPE` is correct

### Local Development Without Entra ID

Leave `ENTRA_TENANT_ID` empty in `src/bff/.env` — the BFF auth middleware will pass all requests through without validation. The frontend will show the Sign In button but won't be able to authenticate until MSAL is configured.
