'use client';

/**
 * TelemetryProvider — bootstraps Application Insights in the browser.
 *
 * Renders no UI; purely fetches the App Insights connection string from the
 * `/api/config/telemetry` runtime config endpoint and initialises the SDK on
 * mount.  Route-change page views are handled automatically by the SDK's
 * `enableAutoRouteTracking` option.
 *
 * Using a runtime config endpoint (rather than `NEXT_PUBLIC_*` env vars)
 * allows the same Docker image to be promoted across environments with
 * different telemetry configuration injected at runtime.
 *
 * Must be rendered inside the Next.js App Router client boundary.
 */

import { useEffect } from 'react';
import { initAppInsights } from '@/lib/telemetry/app-insights-browser';

export default function TelemetryProvider() {
  useEffect(() => {
    fetch('/api/config/telemetry')
      .then((res) => res.json())
      .then(({ connectionString }: { connectionString: string }) => {
        initAppInsights(connectionString);
      })
      .catch(() => {
        // Telemetry is non-critical; swallow fetch/init errors silently.
      });
  }, []);

  return null;
}
