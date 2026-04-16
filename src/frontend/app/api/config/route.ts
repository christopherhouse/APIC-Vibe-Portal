/**
 * Runtime configuration endpoint.
 *
 * Serves environment-specific configuration to the frontend at runtime.
 * This allows the same Docker image to be deployed across dev, staging, and prod
 * by injecting environment variables at container startup instead of baking them
 * into the image at build time.
 *
 * The response is cached for 1 hour to reduce load, but still allows config updates
 * without rebuilding the image.
 */

import { NextResponse } from 'next/server';

export interface RuntimeConfig {
  msal: {
    clientId: string;
    authority: string;
    redirectUri: string;
  };
  bffApiScope: string;
}

/**
 * GET /api/config
 *
 * Returns runtime configuration for the frontend.
 * Uses standard env vars (not NEXT_PUBLIC_*) so they can be set at container runtime.
 */
export async function GET() {
  // Read from standard env vars (not NEXT_PUBLIC_*)
  // These will be injected by the Container Apps deployment at runtime
  const clientId = process.env.MSAL_CLIENT_ID ?? '';
  const tenantId = process.env.MSAL_TENANT_ID ?? '';
  const redirectUri = process.env.MSAL_REDIRECT_URI ?? 'http://localhost:3000';
  const bffApiScope = process.env.BFF_API_SCOPE ?? '';

  // Validate required config
  const missing: string[] = [];
  if (!clientId) missing.push('MSAL_CLIENT_ID');
  if (!tenantId) missing.push('MSAL_TENANT_ID');

  if (missing.length > 0) {
    console.error(
      `[Runtime Config] Missing required environment variable(s): ${missing.join(', ')}. ` +
        'Entra ID authentication will not work. ' +
        'Ensure these are set in your Container App environment variables or .env.local for local dev.'
    );
  }

  const config: RuntimeConfig = {
    msal: {
      clientId,
      authority: `https://login.microsoftonline.com/${tenantId}`,
      redirectUri,
    },
    bffApiScope,
  };

  return NextResponse.json(config, {
    headers: {
      // Cache for 1 hour — config rarely changes, but we want to allow updates without restarting
      'Cache-Control': 'public, max-age=3600, stale-while-revalidate=86400',
    },
  });
}
