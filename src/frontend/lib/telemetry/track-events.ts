/**
 * Typed telemetry event tracking functions.
 *
 * Each function corresponds to a specific user action or application event.
 * They delegate to Application Insights `trackEvent` / `trackException` so
 * the call sites stay clean and the event schema stays consistent.
 */

'use client';

import { getAppInsights } from './app-insights-browser';

// ---------------------------------------------------------------------------
// Event helpers
// ---------------------------------------------------------------------------

/** Track a search query with result count and duration. */
export function trackSearchPerformed(params: {
  query: string;
  resultCount: number;
  durationMs: number;
}): void {
  getAppInsights()?.trackEvent({
    name: 'search_performed',
    properties: {
      query: params.query,
      resultCount: params.resultCount,
      durationMs: params.durationMs,
    },
  });
}

/** Track when a user views an API detail page. */
export function trackApiViewed(params: {
  apiId: string;
  source: 'catalog' | 'search' | 'chat';
}): void {
  getAppInsights()?.trackEvent({
    name: 'api_viewed',
    properties: {
      apiId: params.apiId,
      source: params.source,
    },
  });
}

/** Track a chat message sent by the user. */
export function trackChatMessageSent(params: { messageLength: number; sessionId: string }): void {
  getAppInsights()?.trackEvent({
    name: 'chat_message_sent',
    properties: {
      messageLength: params.messageLength,
      sessionId: params.sessionId,
    },
  });
}

/** Track a catalog/search filter being applied. */
export function trackFilterApplied(params: { filterType: string; filterValue: string }): void {
  getAppInsights()?.trackEvent({
    name: 'filter_applied',
    properties: {
      filterType: params.filterType,
      filterValue: params.filterValue,
    },
  });
}

/** Track an API spec download. */
export function trackSpecDownloaded(params: { apiId: string; format: string }): void {
  getAppInsights()?.trackEvent({
    name: 'spec_downloaded',
    properties: {
      apiId: params.apiId,
      format: params.format,
    },
  });
}

/** Track a caught application error with optional context. */
export function trackError(error: Error, properties?: Record<string, string>): void {
  getAppInsights()?.trackException({ exception: error, properties });
}
