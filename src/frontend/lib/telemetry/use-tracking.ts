/**
 * React hook for Application Insights event tracking.
 *
 * Provides a stable `track` object with typed helpers so components can
 * instrument user interactions without coupling to the SDK directly.
 *
 * @example
 * ```tsx
 * const { track } = useTracking();
 * <button onClick={() => track.searchPerformed({ query, resultCount, durationMs })}>
 *   Search
 * </button>
 * ```
 */

'use client';

import { useMemo } from 'react';
import {
  trackApiViewed,
  trackChatMessageSent,
  trackError,
  trackFilterApplied,
  trackSearchPerformed,
  trackSpecDownloaded,
} from './track-events';

interface TrackingHelpers {
  searchPerformed: typeof trackSearchPerformed;
  apiViewed: typeof trackApiViewed;
  chatMessageSent: typeof trackChatMessageSent;
  filterApplied: typeof trackFilterApplied;
  specDownloaded: typeof trackSpecDownloaded;
  error: typeof trackError;
}

/**
 * Return a stable object of typed telemetry tracking helpers.
 *
 * The returned object is memoized so it is safe to include in dependency arrays.
 */
export function useTracking(): { track: TrackingHelpers } {
  const track = useMemo<TrackingHelpers>(
    () => ({
      searchPerformed: trackSearchPerformed,
      apiViewed: trackApiViewed,
      chatMessageSent: trackChatMessageSent,
      filterApplied: trackFilterApplied,
      specDownloaded: trackSpecDownloaded,
      error: trackError,
    }),
    []
  );

  return { track };
}
