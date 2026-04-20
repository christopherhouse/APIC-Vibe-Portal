# Runtime Configuration

## Problem

Previously, Next.js `NEXT_PUBLIC_*` variables were baked into the Docker image at build time. This meant:
- Each environment required a separate image build
- Images couldn't be promoted across environments
- Config changes required a full rebuild and redeploy

## Solution

MSAL configuration is now injected at **runtime** via environment variables on the Container App. The same Docker image is built once and deployed to all environments.

## How It Works

```
Docker Image (built once, promoted across envs)
  │
  ├── /api/config/msal   ←── reads process.env at runtime
  │                              MSAL_CLIENT_ID
  │                              MSAL_AUTHORITY
  │                              MSAL_REDIRECT_URI
  │                              BFF_API_SCOPE
  │
  └── AuthProvider       ←── fetches /api/config/msal on startup
                                initializes MSAL with runtime values

Container App (dev/staging/prod)
  │
  └── injects env vars at deploy time
       MSAL_CLIENT_ID   = <env-specific value>
       MSAL_AUTHORITY   = <env-specific value>
       MSAL_REDIRECT_URI = <env-specific value>
       BFF_API_SCOPE    = <env-specific value>
```

## Environment Variables

| Variable | Example (dev) | Description |
|----------|---------------|-------------|
| `MSAL_CLIENT_ID` | `12345678-1234-1234-1234-123456789abc` | SPA app registration client ID |
| `MSAL_AUTHORITY` | `https://login.microsoftonline.com/<tenant-id>` | Entra authority URL |
| `MSAL_REDIRECT_URI` | `https://apic-portal-dev.azurecontainerapps.io` | Post-login redirect |
| `BFF_API_SCOPE` | `api://12345678-...def/.default` | BFF OAuth scope |

## Local Development

Create `src/frontend/.env.local`:

```env
MSAL_CLIENT_ID=your-spa-client-id
MSAL_AUTHORITY=https://login.microsoftonline.com/your-tenant-id
MSAL_REDIRECT_URI=http://localhost:3000
BFF_API_SCOPE=api://your-bff-client-id/.default
```

Next.js loads `.env.local` automatically; the `/api/config/msal` endpoint serves these values to the browser.

## GitHub Actions Variables

Set these as GitHub environment variables (Settings → Environments → select env → Environment variables):

| Variable | Set In |
|----------|--------|
| `MSAL_CLIENT_ID` | Each environment (`dev`, `staging`, `prod`) |
| `MSAL_AUTHORITY` | Each environment |
| `MSAL_REDIRECT_URI` | Each environment |
| `BFF_API_SCOPE` | Each environment |

The `deploy-app.yml` workflow passes these to `scripts/deploy-container-apps.sh` via `--frontend-env-vars`.

## Benefits

- ✅ Build once, deploy everywhere
- ✅ Test the exact same artifact in lower environments before production
- ✅ Config changes don't require rebuilds
- ✅ Follows twelve-factor app principles
- ✅ No secrets baked into images

## Key Files

| File | Purpose |
|------|---------|
| `src/frontend/app/api/config/msal/route.ts` | API endpoint that serves runtime config |
| `src/frontend/lib/auth/msal-config.ts` | Config fetcher and MSAL config builder |
| `src/frontend/lib/auth/auth-provider.tsx` | AuthProvider that fetches config asynchronously |
| `scripts/deploy-container-apps.sh` | Injects env vars into Container App at deploy time |
| `.github/workflows/deploy-app.yml` | CI/CD workflow |

## Related

- [[Authentication and RBAC]] — Entra ID setup
- [[CI-CD Pipeline]] — Deployment workflow
- [[Getting Started]] — Local `.env.local` setup
