/**
 * Typed analytics event models for the APIC Vibe Portal.
 *
 * All event types capture behavioural metadata only — raw user IDs and query
 * strings are never stored.  User identifiers are hashed server-side; search
 * queries are replaced by their length and a salted hash.
 */

// ---------------------------------------------------------------------------
// Individual event types
// ---------------------------------------------------------------------------

/** Page view event — fired on every route change. */
export interface PageViewEvent {
  type: 'page_view';
  /** The page path (e.g. "/catalog", "/search"). */
  page: string;
  /** Time spent on the previous page in milliseconds. */
  duration?: number;
}

/** Search query event — privacy-safe: stores hash and metadata, not raw text. */
export interface SearchQueryEvent {
  type: 'search_query';
  /** Salted SHA-256 hash of the query string (never the raw text). */
  queryHash: string;
  /** Character length of the query for volume analytics. */
  queryLength: number;
  /** Number of results returned by the search. */
  resultCount: number;
  /** API ID of the result the user clicked, if any. */
  clickedResult?: string;
}

/** API detail view event. */
export interface ApiViewEvent {
  type: 'api_view';
  /** Identifier of the API that was viewed. */
  apiId: string;
  /** How the user arrived at the API detail page. */
  source: 'catalog' | 'search' | 'chat' | 'compare';
}

/** API spec download event. */
export interface SpecDownloadEvent {
  type: 'spec_download';
  /** Identifier of the API whose spec was downloaded. */
  apiId: string;
  /** Format of the downloaded specification. */
  format: 'json' | 'yaml';
}

/** Chat interaction event — captures metadata only, never message content. */
export interface ChatInteractionEvent {
  type: 'chat_interaction';
  /** Anonymised chat conversation identifier (distinct from the analytics session ID). */
  chatSessionId: string;
  /** Number of messages exchanged in the session. */
  messageCount: number;
  /** Name of the AI agent that handled the session. */
  agentUsed: string;
}

/** API comparison event. */
export interface ComparisonMadeEvent {
  type: 'comparison_made';
  /** Identifiers of the APIs that were compared. */
  apiIds: string[];
  /** Whether the user invoked AI-powered comparison analysis. */
  usedAiAnalysis: boolean;
}

/** Governance panel view event. */
export interface GovernanceViewedEvent {
  type: 'governance_viewed';
  /** API whose governance panel was viewed, if applicable. */
  apiId?: string;
  /** Section of the governance panel that was viewed. */
  section: string;
}

/** Filter applied event — fired when a catalog or search filter is changed. */
export interface FilterAppliedEvent {
  type: 'filter_applied';
  /** Type of filter (e.g. "tag", "lifecycle", "kind"). */
  filterType: string;
  /** Value selected for the filter. */
  filterValue: string;
  /** UI context where the filter was applied (e.g. "catalog", "search"). */
  context: string;
}

/** User session summary event — sent on session end or page unload. */
export interface UserSessionEvent {
  type: 'user_session';
  /** Total session duration in seconds. */
  sessionDuration: number;
  /** Total number of pages visited in this session. */
  pagesVisited: number;
}

// ---------------------------------------------------------------------------
// Union type
// ---------------------------------------------------------------------------

/** Union of all analytics event payloads. */
export type AnalyticsEvent =
  | PageViewEvent
  | SearchQueryEvent
  | ApiViewEvent
  | SpecDownloadEvent
  | ChatInteractionEvent
  | ComparisonMadeEvent
  | GovernanceViewedEvent
  | FilterAppliedEvent
  | UserSessionEvent;

// ---------------------------------------------------------------------------
// Envelope and batch types
// ---------------------------------------------------------------------------

/**
 * A single analytics event wrapped with client-side context metadata.
 *
 * This is the unit that travels from the frontend to the BFF.
 */
export interface AnalyticsEventEnvelope {
  /** The event payload. */
  event: AnalyticsEvent;
  /** ISO-8601 timestamp when the event occurred on the client. */
  clientTimestamp: string;
  /** The page path where the event was triggered. */
  pagePath: string;
  /** Anonymised session identifier. */
  sessionId?: string;
}

/** Batch of event envelopes submitted to the BFF in a single request. Must contain at least one event. */
export interface AnalyticsEventBatch {
  /** Non-empty array of event envelopes.  The BFF will reject an empty batch with 422. */
  events: [AnalyticsEventEnvelope, ...AnalyticsEventEnvelope[]];
}
