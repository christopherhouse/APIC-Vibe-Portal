/**
 * Application Insights browser SDK initialization.
 *
 * Initializes the `@microsoft/applicationinsights-web` SDK once with W3C
 * Trace Context propagation enabled so that browser → BFF requests carry a
 * `traceparent` header for end-to-end distributed tracing.
 *
 * The SDK is configured lazily and only activates when
 * `NEXT_PUBLIC_APPLICATIONINSIGHTS_CONNECTION_STRING` is set, so local
 * development runs without any telemetry overhead.
 */

'use client';

import { ApplicationInsights } from '@microsoft/applicationinsights-web';

let appInsights: ApplicationInsights | null = null;
let initialized = false;

/**
 * Return the shared `ApplicationInsights` instance, initializing it on the
 * first call.  Returns `null` when the connection string is not configured.
 */
export function getAppInsights(): ApplicationInsights | null {
  if (initialized) return appInsights;
  initialized = true;

  const connectionString =
    process.env.NEXT_PUBLIC_APPLICATIONINSIGHTS_CONNECTION_STRING;
  if (!connectionString) return null;

  appInsights = new ApplicationInsights({
    config: {
      connectionString,
      enableAutoRouteTracking: true,
      enableCorsCorrelation: true,
      enableRequestHeaderTracking: true,
      enableResponseHeaderTracking: true,
      distributedTracingMode: 2, // W3C Trace Context
      disableFetchTracking: false,
      autoTrackPageVisitTime: true,
    },
  });

  appInsights.loadAppInsights();
  appInsights.trackPageView();

  return appInsights;
}

/**
 * Initialise App Insights and set up global unhandled-error capture.
 *
 * Call once from the root client layout component.
 */
export function initAppInsights(): void {
  const ai = getAppInsights();
  if (!ai) return;

  // Capture unhandled promise rejections
  if (typeof window !== 'undefined') {
    window.addEventListener('unhandledrejection', (event) => {
      ai.trackException({
        exception: new Error(
          event.reason instanceof Error
            ? event.reason.message
            : String(event.reason),
        ),
        properties: { type: 'unhandledrejection' },
      });
    });
  }
}
