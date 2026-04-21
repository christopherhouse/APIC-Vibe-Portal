/**
 * AnalyticsProvider — React context provider for client-side analytics.
 *
 * Responsibilities:
 * - Creates and owns a single `EventBuffer` instance.
 * - Generates a short anonymised session ID on mount.
 * - Tracks page views automatically when the Next.js pathname changes.
 * - Respects the browser's Do Not Track preference.
 * - Flushes the buffer on page unload (`visibilitychange` + `beforeunload`).
 * - Destroys the buffer timer on unmount to prevent memory leaks.
 *
 * Wrap the application root (or a sub-tree) with this provider to enable the
 * `useAnalytics()` hook in descendant components.
 *
 * @example
 * ```tsx
 * // app/layout.tsx
 * <AnalyticsProvider>
 *   {children}
 * </AnalyticsProvider>
 * ```
 */

'use client';

import { createContext, useEffect, useMemo, useRef } from 'react';
import { usePathname } from 'next/navigation';
import { EventBuffer, isDoNotTrackEnabled } from './event-buffer';

// ---------------------------------------------------------------------------
// Context value
// ---------------------------------------------------------------------------

export interface AnalyticsContextValue {
  /** Shared event buffer for the session. */
  buffer: EventBuffer;
  /** Short anonymised session identifier. */
  sessionId: string;
}

export const AnalyticsContext = createContext<AnalyticsContextValue | null>(null);

// ---------------------------------------------------------------------------
// Session ID generation
// ---------------------------------------------------------------------------

/**
 * Generate a short random session ID.
 *
 * Uses `crypto.randomUUID()` when available; falls back to a simple
 * `Math.random()`-based string for environments that lack the API.
 */
function generateSessionId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

// ---------------------------------------------------------------------------
// Provider component
// ---------------------------------------------------------------------------

export interface AnalyticsProviderProps {
  children: React.ReactNode;
  /**
   * Override the flush endpoint (useful for testing).
   * Defaults to "/api/analytics/events".
   */
  endpoint?: string;
  /** Override the fetch function (useful for testing). */
  fetchFn?: typeof fetch;
}

export default function AnalyticsProvider({ children, endpoint, fetchFn }: AnalyticsProviderProps) {
  const pathname = usePathname();
  const sessionId = useMemo(() => generateSessionId(), []);

  // Create the buffer once for the lifetime of the provider.
  const buffer = useMemo(
    () => new EventBuffer({ endpoint, fetchFn }),
    [] // endpoint and fetchFn intentionally excluded: buffer is created once per mount
  );

  // Track page views on pathname changes.
  const prevPathnameRef = useRef<string | null>(null);
  const pageEnterTimeRef = useRef<number>(Date.now());

  useEffect(() => {
    if (isDoNotTrackEnabled()) return;

    const now = Date.now();
    const prev = prevPathnameRef.current;

    if (prev !== null && prev !== pathname) {
      // Record duration for the page we're leaving.
      const duration = now - pageEnterTimeRef.current;
      buffer.push({
        event: { type: 'page_view', page: prev, duration },
        clientTimestamp: new Date(pageEnterTimeRef.current).toISOString(),
        pagePath: prev,
        sessionId,
      });
    } else if (prev === null) {
      // First render — track initial page view without duration.
      buffer.push({
        event: { type: 'page_view', page: pathname },
        clientTimestamp: new Date().toISOString(),
        pagePath: pathname,
        sessionId,
      });
    }

    prevPathnameRef.current = pathname;
    pageEnterTimeRef.current = now;
  }, [pathname, buffer, sessionId]);

  // Flush on page hide / unload.
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'hidden') {
        void buffer.flush();
      }
    };
    const handleBeforeUnload = () => {
      void buffer.flush();
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [buffer]);

  // Destroy the buffer timer on unmount.
  useEffect(() => {
    return () => {
      buffer.destroy();
    };
  }, [buffer]);

  const value = useMemo<AnalyticsContextValue>(() => ({ buffer, sessionId }), [buffer, sessionId]);

  return <AnalyticsContext.Provider value={value}>{children}</AnalyticsContext.Provider>;
}
