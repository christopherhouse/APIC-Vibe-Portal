'use client';

/**
 * TelemetryProvider — bootstraps Application Insights in the browser.
 *
 * Renders no UI; purely initialises the App Insights SDK on mount and
 * tracks page views on route changes.  Must be rendered inside the Next.js
 * App Router client boundary.
 */

import { useEffect } from 'react';
import { initAppInsights, getAppInsights } from '@/lib/telemetry/app-insights-browser';
import { usePathname, useSearchParams } from 'next/navigation';

export default function TelemetryProvider() {
  // Initialise once on mount
  useEffect(() => {
    initAppInsights();
  }, []);

  const pathname = usePathname();
  const searchParams = useSearchParams();

  // Track page views on client-side navigation
  useEffect(() => {
    const ai = getAppInsights();
    if (ai) {
      ai.trackPageView({ uri: pathname + (searchParams?.toString() ? `?${searchParams.toString()}` : '') });
    }
  }, [pathname, searchParams]);

  return null;
}
