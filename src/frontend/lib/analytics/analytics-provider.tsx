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
 * Generate a short random session ID using the Web Crypto API.
 *
 * Uses `crypto.randomUUID()` when available (all modern browsers and Node 14.17+).
 * Falls back to `crypto.getRandomValues()` for environments that have the API but
 * lack `randomUUID`.
 */
function generateSessionId(): string {
  if (typeof crypto !== 'undefined') {
    if (typeof crypto.randomUUID === 'function') {
      return crypto.randomUUID();
    }
    if (typeof crypto.getRandomValues === 'function') {
      const bytes = new Uint8Array(16);
      crypto.getRandomValues(bytes);
      return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
    }
  }
  // Last resort: use Date.now with a counter to guarantee uniqueness within a session.
  return `${Date.now().toString(36)}-${(++_sessionCounter).toString(36)}`;
}

let _sessionCounter = 0;

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
      // Record the exit event for the page we're leaving (with duration).
      const duration = now - pageEnterTimeRef.current;
      buffer.push({
        event: { type: 'page_view', page: prev, duration },
        clientTimestamp: new Date(pageEnterTimeRef.current).toISOString(),
        pagePath: prev,
        sessionId,
      });

      // Record the entry event for the page we're entering (no duration yet).
      buffer.push({
        event: { type: 'page_view', page: pathname },
        clientTimestamp: new Date(now).toISOString(),
        pagePath: pathname,
        sessionId,
      });
    } else if (prev === null) {
      // First render — track initial page view without duration.
      buffer.push({
        event: { type: 'page_view', page: pathname },
        clientTimestamp: new Date(now).toISOString(),
        pagePath: pathname,
        sessionId,
      });
    }

    prevPathnameRef.current = pathname;
    pageEnterTimeRef.current = now;
  }, [pathname, buffer, sessionId]);

  // Flush on page hide / unload, capturing the last page's duration.
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'hidden') {
        if (!isDoNotTrackEnabled() && prevPathnameRef.current !== null) {
          const duration = Date.now() - pageEnterTimeRef.current;
          buffer.push({
            event: { type: 'page_view', page: prevPathnameRef.current, duration },
            clientTimestamp: new Date(pageEnterTimeRef.current).toISOString(),
            pagePath: prevPathnameRef.current,
            sessionId,
          });
        }
        void buffer.flush();
      }
    };
    const handleBeforeUnload = () => {
      if (!isDoNotTrackEnabled() && prevPathnameRef.current !== null) {
        const duration = Date.now() - pageEnterTimeRef.current;
        buffer.push({
          event: { type: 'page_view', page: prevPathnameRef.current, duration },
          clientTimestamp: new Date(pageEnterTimeRef.current).toISOString(),
          pagePath: prevPathnameRef.current,
          sessionId,
        });
      }
      void buffer.flush();
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [buffer, sessionId]);

  // Destroy the buffer timer on unmount.
  useEffect(() => {
    return () => {
      buffer.destroy();
    };
  }, [buffer]);

  const value = useMemo<AnalyticsContextValue>(() => ({ buffer, sessionId }), [buffer, sessionId]);

  return <AnalyticsContext.Provider value={value}>{children}</AnalyticsContext.Provider>;
}
