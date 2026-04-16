# Migration Summary: Build-Time to Runtime Environment Configuration

## What Changed

Successfully migrated the APIC Vibe Portal frontend from build-time `NEXT_PUBLIC_*` environment variables to runtime configuration, enabling proper twelve-factor app compliance and image promotion across environments.

## Implementation Summary

### 1. Created Runtime Configuration API
- **New file**: `src/frontend/app/api/config/msal/route.ts`
- **Purpose**: Server-side API endpoint that reads `process.env` and serves MSAL config to browser
- **Returns**: JSON with `clientId`, `authority`, `redirectUri`, `bffApiScope`

### 2. Refactored MSAL Configuration Module
- **Updated**: `src/frontend/lib/auth/msal-config.ts`
- **Changes**:
  - Added `fetchMsalConfig()` to fetch from `/api/config/msal`
  - Added `buildMsalConfig()` to construct MSAL browser config from runtime values
  - Added `buildLoginRequest()` to construct login request from runtime values
  - Removed static `msalConfig`, `loginRequest`, `bffApiScope` exports

### 3. Updated Authentication Provider
- **Updated**: `src/frontend/lib/auth/auth-provider.tsx`
- **Changes**:
  - Fetches config via `fetchMsalConfig()` during initialization
  - Creates MSAL instance with runtime config
  - Provides config to component tree via `MsalConfigContext`
  - Added error handling for config fetch failures

### 4. Created Configuration Context
- **New file**: `src/frontend/lib/auth/msal-config-context.tsx`
- **Purpose**: React context to share runtime config across components
- **Exports**: `MsalConfigProvider`, `useMsalConfig()` hook

### 5. Updated Authentication Hook
- **Updated**: `src/frontend/lib/auth/use-auth.ts`
- **Changes**: Uses `useMsalConfig()` to access runtime config for token acquisition

### 6. Updated Docker Build
- **Updated**: `src/frontend/Dockerfile`
- **Removed**: `ARG NEXT_PUBLIC_*` declarations
- **Result**: No build-time environment variables needed

### 7. Updated CI/CD Pipeline
- **Updated**: `.github/workflows/deploy-app.yml`
- **Removed**: `build-args` from Docker build step
- **Added**: `--frontend-env-vars` parameter to deployment script calls (all environments)

### 8. Updated Deployment Script
- **Updated**: `scripts/deploy-container-apps.sh`
- **Added**: `--frontend-env-vars` flag support
- **Changes**: Injects runtime env vars into Container App during deployment

### 9. Updated Environment Variables
- **Updated**: `.env.example`
- **Changed names**:
  - `NEXT_PUBLIC_MSAL_CLIENT_ID` → `MSAL_CLIENT_ID`
  - `NEXT_PUBLIC_MSAL_AUTHORITY` → `MSAL_AUTHORITY`
  - `NEXT_PUBLIC_MSAL_REDIRECT_URI` → `MSAL_REDIRECT_URI`
  - `NEXT_PUBLIC_BFF_API_SCOPE` → `BFF_API_SCOPE`

### 10. Updated Documentation
- **Updated**: `docs/ENTRA-SETUP.md` - Reflects new variable names and explains migration
- **Created**: `docs/RUNTIME-CONFIG.md` - Comprehensive guide to runtime config architecture
- **Updated**: Auth module exports in `src/frontend/lib/auth/index.ts`

## Benefits Achieved

✅ **Single Artifact Deployment** — Build Docker image once, deploy to all environments
✅ **Environment Parity** — Test exact same artifact in dev/staging before prod
✅ **Configuration Flexibility** — Change config without rebuilding images
✅ **Twelve-Factor App Compliance** — Configuration stored in environment, not code
✅ **Security** — No credentials baked into images
✅ **Faster Deployments** — Config changes don't require rebuilds

## Environment Variable Configuration

### GitHub Actions (per environment)
Add these as GitHub environment variables for each environment (dev, staging, prod):

```
MSAL_CLIENT_ID=<spa-client-id>
MSAL_AUTHORITY=https://login.microsoftonline.com/<tenant-id>
MSAL_REDIRECT_URI=https://<environment-frontend-url>
BFF_API_SCOPE=api://<bff-client-id>/.default
```

### Local Development
Create `src/frontend/.env.local`:

```env
MSAL_CLIENT_ID=your-spa-client-id
MSAL_AUTHORITY=https://login.microsoftonline.com/your-tenant-id
MSAL_REDIRECT_URI=http://localhost:3000
BFF_API_SCOPE=api://your-bff-client-id/.default
```

## Architecture Flow

```
Build Time:
  Docker Build → No env vars injected → Generic image created

Deployment Time (per environment):
  Generic Image → Container App created → Env vars injected via --frontend-env-vars

Runtime:
  Browser → AuthProvider → fetch('/api/config/msal') → Next.js API reads process.env → Returns config → MSAL initialized
```

## Files Modified

### Code Changes (9 files)
1. `src/frontend/app/api/config/msal/route.ts` - NEW
2. `src/frontend/lib/auth/msal-config.ts` - REFACTORED
3. `src/frontend/lib/auth/msal-config-context.tsx` - NEW
4. `src/frontend/lib/auth/auth-provider.tsx` - UPDATED
5. `src/frontend/lib/auth/use-auth.ts` - UPDATED
6. `src/frontend/lib/auth/index.ts` - UPDATED
7. `src/frontend/Dockerfile` - SIMPLIFIED
8. `.github/workflows/deploy-app.yml` - UPDATED
9. `scripts/deploy-container-apps.sh` - ENHANCED

### Documentation (3 files)
1. `.env.example` - UPDATED
2. `docs/ENTRA-SETUP.md` - UPDATED
3. `docs/RUNTIME-CONFIG.md` - NEW

## Next Steps

### Required Before Merge
1. **Update tests** - Auth provider tests need to mock `fetch('/api/config/msal')`
2. **Test locally** - Verify auth flow works with `.env.local`
3. **Validate build** - Ensure Docker build succeeds without NEXT_PUBLIC_* args

### Required Before First Deployment
1. **Configure GitHub environment variables** - Add `MSAL_*` and `BFF_API_SCOPE` to all environments
2. **Update Entra ID redirect URIs** - Match `MSAL_REDIRECT_URI` for each environment

## Migration Notes

- **Breaking Change**: Old `NEXT_PUBLIC_*` variables no longer work
- **Backward Compatibility**: None - this is a clean break
- **Rollback**: Revert to commit before this migration
- **Testing**: All three environments (dev/staging/prod) must be updated together

## References

- **Documentation**: `docs/RUNTIME-CONFIG.md`
- **Next.js Docs**: https://nextjs.org/docs/app/guides/environment-variables#runtime-environment-variables
- **Twelve-Factor App**: https://12factor.net/config
