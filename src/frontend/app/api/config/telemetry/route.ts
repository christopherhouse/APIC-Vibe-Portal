/**
 * Telemetry Configuration API Route
 *
 * Serves the Application Insights connection string to the browser from a
 * server-side environment variable.  This allows the same Docker image to be
 * deployed across environments with different telemetry configuration injected
 * at runtime via Container App environment variables.
 *
 * Why this approach:
 * - NEXT_PUBLIC_* vars are baked into the Docker image at build time
 * - Build-time vars prevent "build once, promote across environments" deployments
 * - This API reads the server-side env var at request time
 * - The same image can send telemetry to a different App Insights workspace per env
 *
 * The connection string is NOT a secret (it identifies the destination workspace
 * but does not grant write access beyond telemetry ingestion), so returning it
 * as plain JSON from a server route is safe.  Do not serve Key Vault secrets
 * or auth credentials from this endpoint.
 */

import { NextResponse } from 'next/server';

export interface TelemetryConfig {
  connectionString: string;
}

/**
 * GET /api/config/telemetry
 *
 * Returns the Application Insights connection string for the current
 * environment.  Called once during client-side application initialisation by
 * `TelemetryProvider`.
 *
 * Returns an empty `connectionString` when the env var is not set — in that
 * case the browser SDK is not initialised and all tracking calls are no-ops.
 */
export async function GET() {
  const config: TelemetryConfig = {
    // Standard Azure Monitor env var name used by the BFF and the OTel distro
    connectionString: process.env.APPLICATIONINSIGHTS_CONNECTION_STRING ?? '',
  };

  return NextResponse.json(config);
}
