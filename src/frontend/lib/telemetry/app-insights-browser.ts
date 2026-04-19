/**
 * Application Insights browser SDK initialization.
 *
 * Initializes the `@microsoft/applicationinsights-web` SDK once with W3C
 * Trace Context propagation enabled so that browser → BFF requests carry a
 * `traceparent` header for end-to-end distributed tracing.
 *
 * The connection string is supplied at call-time by `TelemetryProvider` which
 * fetches it from the `/api/config/telemetry` runtime config endpoint.  This
 * avoids baking the value into the Docker image at build time (a `NEXT_PUBLIC_*`
 * limitation) and allows the same image to be promoted across environments.
 *
 * The SDK is configured lazily and only activates when a non-empty connection
 * string is provided, so local development runs without any telemetry overhead.
 */

'use client';

import { ApplicationInsights, DistributedTracingModes } from '@microsoft/applicationinsights-web';

let appInsights: ApplicationInsights | null = null;
let initialized = false;
let _unhandledRejectionRegistered = false;

/**
 * Return the shared `ApplicationInsights` instance.
 *
 * Returns `null` when `initAppInsights` has not yet been called or when the
 * connection string was not provided.
 */
export function getAppInsights(): ApplicationInsights | null {
  return appInsights;
}

/**
 * Initialise App Insights with the supplied connection string.
 *
 * Safe to call multiple times — only the first call with a non-empty
 * connection string has any effect.  Subsequent calls are no-ops.
 *
 * @param connectionString - Application Insights connection string obtained
 *   from the `/api/config/telemetry` runtime config endpoint.
 */
export function initAppInsights(connectionString: string): void {
  if (initialized) return;
  initialized = true;

  if (!connectionString) return;

  appInsights = new ApplicationInsights({
    config: {
      connectionString,
      // enableAutoRouteTracking handles page-view tracking on route changes via
      // the History API — no need for manual trackPageView() calls.
      enableAutoRouteTracking: true,
      enableCorsCorrelation: true,
      enableRequestHeaderTracking: true,
      enableResponseHeaderTracking: true,
      distributedTracingMode: DistributedTracingModes.W3C,
      disableFetchTracking: false,
      autoTrackPageVisitTime: true,
    },
  });

  appInsights.loadAppInsights();

  // Capture unhandled promise rejections.  The guard ensures the listener is
  // registered only once even if React Strict Mode double-invokes effects.
  if (typeof window !== 'undefined' && !_unhandledRejectionRegistered) {
    _unhandledRejectionRegistered = true;
    window.addEventListener('unhandledrejection', (event) => {
      appInsights?.trackException({
        exception: new Error(
          event.reason instanceof Error ? event.reason.message : String(event.reason)
        ),
        properties: { type: 'unhandledrejection' },
      });
    });
  }
}
