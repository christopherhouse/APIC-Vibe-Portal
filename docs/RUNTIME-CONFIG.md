# Runtime Environment Configuration — Frontend MSAL

This document explains how the frontend MSAL (Microsoft Authentication Library) configuration is handled at runtime, allowing the same Docker image to be deployed across multiple environments with different configuration values.

## Problem

Previously, Next.js environment variables prefixed with `NEXT_PUBLIC_*` were **baked into the Docker image at build time**. This meant:

- ❌ Each environment (dev/staging/prod) required a separate Docker image build
- ❌ Images couldn't be promoted across environments (violates twelve-factor app principles)
- ❌ Configuration changes required rebuilding and redeploying images
- ❌ No way to test the exact same artifact in lower environments before promoting to production

## Solution

We now use **runtime configuration** by:

1. **Removing `NEXT_PUBLIC_*` prefixes** — Variables are now server-side only
2. **Creating an API endpoint** (`/api/config/msal`) that reads server-side env vars and serves them to the browser
3. **Fetching config at application startup** — The AuthProvider fetches config before initializing MSAL
4. **Injecting values at deployment time** — Container App environment variables are set per environment

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Docker Image (built once, promoted across envs)                │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Next.js Frontend                                            │ │
│  │                                                              │ │
│  │  ┌──────────────────┐         ┌─────────────────────────┐  │ │
│  │  │  Client Component│         │  API Route              │  │ │
│  │  │  (AuthProvider)  │         │  /api/config/msal       │  │ │
│  │  │                  │         │                         │  │ │
│  │  │  1. Fetch config │────────►│  2. Read process.env    │  │ │
│  │  │                  │◄────────│     - MSAL_CLIENT_ID    │  │ │
│  │  │  3. Initialize   │         │     - MSAL_AUTHORITY    │  │ │
│  │  │     MSAL with    │         │     - MSAL_REDIRECT_URI │  │ │
│  │  │     runtime cfg  │         │     - BFF_API_SCOPE     │  │ │
│  │  └──────────────────┘         └─────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                  ▲
                                  │
                    Environment variables injected
                    by Azure Container Apps at runtime
                                  │
         ┌────────────────────────┼────────────────────────┐
         │                        │                        │
    ┌────▼────┐            ┌──────▼──────┐        ┌───────▼──────┐
    │   Dev   │            │  Staging    │        │  Production  │
    │         │            │             │        │              │
    │ MSAL_*  │            │  MSAL_*     │        │  MSAL_*      │
    │ = dev   │            │  = staging  │        │  = prod      │
    └─────────┘            └─────────────┘        └──────────────┘
```

## Implementation Details

### 1. API Route (`/api/config/msal/route.ts`)

```typescript
export async function GET() {
  const config: MsalConfig = {
    clientId: process.env.MSAL_CLIENT_ID ?? '',
    authority: process.env.MSAL_AUTHORITY ?? '',
    redirectUri: process.env.MSAL_REDIRECT_URI ?? '',
    bffApiScope: process.env.BFF_API_SCOPE ?? '',
  };

  return NextResponse.json(config);
}
```

### 2. Config Fetcher (`lib/auth/msal-config.ts`)

```typescript
export async function fetchMsalConfig(): Promise<MsalConfig> {
  const response = await fetch('/api/config/msal');
  return await response.json();
}
```

### 3. AuthProvider (`lib/auth/auth-provider.tsx`)

```typescript
useEffect(() => {
  const init = async () => {
    // Fetch runtime MSAL configuration from API
    const config = await fetchMsalConfig();

    // Create MSAL instance with runtime config
    const msalConfig = buildMsalConfig(config);
    msalInstance = new PublicClientApplication(msalConfig);
    await msalInstance.initialize();

    setIsInitialized(true);
  };
  init();
}, []);
```

## Deployment Configuration

### GitHub Actions Variables

Set these as GitHub environment variables (one set per environment):

| Variable Name       | Example Value (dev)                                   |
| ------------------- | ----------------------------------------------------- |
| `MSAL_CLIENT_ID`    | `12345678-1234-1234-1234-123456789abc`                |
| `MSAL_AUTHORITY`    | `https://login.microsoftonline.com/<tenant-id>`       |
| `MSAL_REDIRECT_URI` | `https://apic-portal-dev.azurecontainerapps.io`       |
| `BFF_API_SCOPE`     | `api://12345678-1234-1234-1234-123456789def/.default` |

### Deployment Script

The `deploy-container-apps.sh` script receives these values via the `--frontend-env-vars` flag:

```bash
./deploy-container-apps.sh \
  --frontend-env-vars "MSAL_CLIENT_ID=${{ vars.MSAL_CLIENT_ID }} MSAL_AUTHORITY=... MSAL_REDIRECT_URI=... BFF_API_SCOPE=..."
```

And injects them as Container App environment variables:

```bash
az containerapp create \
  --name "$FRONTEND_APP_NAME" \
  --env-vars "MSAL_CLIENT_ID=... MSAL_AUTHORITY=... MSAL_REDIRECT_URI=... BFF_API_SCOPE=..."
```

## Local Development

Create `src/frontend/.env.local`:

```env
MSAL_CLIENT_ID=your-spa-client-id
MSAL_AUTHORITY=https://login.microsoftonline.com/your-tenant-id
MSAL_REDIRECT_URI=http://localhost:3000
BFF_API_SCOPE=api://your-bff-client-id/.default
```

Next.js automatically loads these during local dev, and the `/api/config/msal` endpoint serves them to the browser.

## Benefits

✅ **Single artifact deployment** — Build once, deploy everywhere
✅ **Environment parity** — Test the exact artifact that goes to production
✅ **Configuration flexibility** — Change config without rebuilding
✅ **Follows twelve-factor app** — Configuration in the environment, not the code
✅ **Secure** — No secrets baked into images
✅ **Fast deployments** — No need to rebuild for config changes

## Migration from NEXT*PUBLIC*\*

If you're upgrading from the previous approach:

1. **Update environment variables** — Remove `NEXT_PUBLIC_` prefix
   - `NEXT_PUBLIC_MSAL_CLIENT_ID` → `MSAL_CLIENT_ID`
   - `NEXT_PUBLIC_MSAL_AUTHORITY` → `MSAL_AUTHORITY`
   - `NEXT_PUBLIC_MSAL_REDIRECT_URI` → `MSAL_REDIRECT_URI`
   - `NEXT_PUBLIC_BFF_API_SCOPE` → `BFF_API_SCOPE`

2. **Update GitHub environment variables** — Rename variables in all environments

3. **Update local `.env.local`** — Use new variable names

4. **Rebuild and redeploy** — The new approach will take effect

## Related Files

- `src/frontend/app/api/config/msal/route.ts` — API endpoint
- `src/frontend/lib/auth/msal-config.ts` — Config fetcher and builder
- `src/frontend/lib/auth/auth-provider.tsx` — Async initialization
- `src/frontend/lib/auth/msal-config-context.tsx` — React context for sharing config
- `scripts/deploy-container-apps.sh` — Deployment script
- `.github/workflows/deploy-app.yml` — CI/CD workflow
