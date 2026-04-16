/**
 * MSAL Configuration API Route
 *
 * Serves runtime MSAL configuration to the browser from server-side environment variables.
 * This allows the same Docker image to be deployed across multiple environments with
 * different configuration values injected at runtime via Container App environment variables.
 *
 * Why this approach:
 * - NEXT_PUBLIC_* vars are baked into the Docker image at build time
 * - Build-time vars prevent image promotion across dev/staging/prod
 * - This API reads server-side env vars at request time
 * - The same image can be configured differently in each environment
 */

import { NextResponse } from 'next/server';

export interface MsalConfig {
  clientId: string;
  authority: string;
  redirectUri: string;
  bffApiScope: string;
}

/**
 * GET /api/config/msal
 *
 * Returns MSAL configuration for the current environment.
 * Called once during application initialization on the client.
 */
export async function GET() {
  // Read from server-side environment variables (NOT NEXT_PUBLIC_*)
  const config: MsalConfig = {
    clientId: process.env.MSAL_CLIENT_ID ?? '',
    authority: process.env.MSAL_AUTHORITY ?? 'https://login.microsoftonline.com/common',
    redirectUri: process.env.MSAL_REDIRECT_URI ?? '',
    bffApiScope: process.env.BFF_API_SCOPE ?? '',
  };

  // Validate required values
  const missing: string[] = [];
  if (!config.clientId) missing.push('MSAL_CLIENT_ID');
  if (!config.redirectUri) missing.push('MSAL_REDIRECT_URI');

  if (missing.length > 0) {
    console.error(
      `[MSAL Config API] Missing required environment variable(s): ${missing.join(', ')}. ` +
        'Entra ID authentication will not work. ' +
        'Ensure these variables are set in the Container App environment or .env.local for local dev.'
    );
  }

  // Return configuration as JSON
  return NextResponse.json(config);
}
