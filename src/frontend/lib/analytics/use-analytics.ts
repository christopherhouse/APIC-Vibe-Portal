/**
 * `useAnalytics` — React hook for submitting analytics events.
 *
 * Returns a stable `track` object whose methods correspond to each analytics
 * event type.  All methods are no-ops when Do Not Track is active.
 *
 * The hook reads the `EventBuffer` and session ID from `AnalyticsContext`.
 *
 * @example
 * ```tsx
 * const { track } = useAnalytics();
 * // ...
 * track.apiView({ apiId: 'my-api', source: 'search' });
 * ```
 */

'use client';

import { useCallback, useContext, useMemo } from 'react';
import type {
  AnalyticsEvent,
  ApiViewEvent,
  ChatInteractionEvent,
  ComparisonMadeEvent,
  FilterAppliedEvent,
  GovernanceViewedEvent,
  SearchQueryEvent,
  SpecDownloadEvent,
} from '@apic-vibe-portal/shared';
import { AnalyticsContext } from './analytics-provider';
import { isDoNotTrackEnabled } from './event-buffer';

// ---------------------------------------------------------------------------
// Track helpers type
// ---------------------------------------------------------------------------

export interface TrackHelpers {
  /** Track a search query event. */
  searchQuery: (params: Omit<SearchQueryEvent, 'type'>) => void;
  /** Track an API detail view. */
  apiView: (params: Omit<ApiViewEvent, 'type'>) => void;
  /** Track a spec download. */
  specDownload: (params: Omit<SpecDownloadEvent, 'type'>) => void;
  /** Track a chat interaction (metadata only — no message content). */
  chatInteraction: (params: Omit<ChatInteractionEvent, 'type'>) => void;
  /** Track an API comparison. */
  comparisonMade: (params: Omit<ComparisonMadeEvent, 'type'>) => void;
  /** Track a governance panel view. */
  governanceViewed: (params: Omit<GovernanceViewedEvent, 'type'>) => void;
  /** Track a filter being applied. */
  filterApplied: (params: Omit<FilterAppliedEvent, 'type'>) => void;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * Return stable typed analytics tracking helpers.
 *
 * All helpers are memoized and safe to include in React dependency arrays.
 * They are silently suppressed when the buffer is not available or when the
 * user has enabled Do Not Track.
 */
export function useAnalytics(): { track: TrackHelpers } {
  const ctx = useContext(AnalyticsContext);

  const push = useCallback(
    (event: AnalyticsEvent) => {
      if (isDoNotTrackEnabled() || !ctx) return;
      ctx.buffer.push({
        event,
        clientTimestamp: new Date().toISOString(),
        pagePath: typeof window !== 'undefined' ? window.location.pathname : '',
        sessionId: ctx.sessionId,
      });
    },
    [ctx]
  );

  const searchQuery = useCallback(
    (params: Omit<SearchQueryEvent, 'type'>) => push({ type: 'search_query', ...params }),
    [push]
  );
  const apiView = useCallback(
    (params: Omit<ApiViewEvent, 'type'>) => push({ type: 'api_view', ...params }),
    [push]
  );
  const specDownload = useCallback(
    (params: Omit<SpecDownloadEvent, 'type'>) => push({ type: 'spec_download', ...params }),
    [push]
  );
  const chatInteraction = useCallback(
    (params: Omit<ChatInteractionEvent, 'type'>) => push({ type: 'chat_interaction', ...params }),
    [push]
  );
  const comparisonMade = useCallback(
    (params: Omit<ComparisonMadeEvent, 'type'>) => push({ type: 'comparison_made', ...params }),
    [push]
  );
  const governanceViewed = useCallback(
    (params: Omit<GovernanceViewedEvent, 'type'>) => push({ type: 'governance_viewed', ...params }),
    [push]
  );
  const filterApplied = useCallback(
    (params: Omit<FilterAppliedEvent, 'type'>) => push({ type: 'filter_applied', ...params }),
    [push]
  );

  const track = useMemo<TrackHelpers>(
    () => ({
      searchQuery,
      apiView,
      specDownload,
      chatInteraction,
      comparisonMade,
      governanceViewed,
      filterApplied,
    }),
    [
      searchQuery,
      apiView,
      specDownload,
      chatInteraction,
      comparisonMade,
      governanceViewed,
      filterApplied,
    ]
  );

  return { track };
}
