/**
 * Tests for analytics event types in the shared package.
 *
 * Verifies that the type definitions can be used correctly and that the
 * AnalyticsEventEnvelope and AnalyticsEventBatch shapes work as expected.
 */

import type {
  AnalyticsEvent,
  AnalyticsEventBatch,
  AnalyticsEventEnvelope,
  ApiViewEvent,
  ChatInteractionEvent,
  ComparisonMadeEvent,
  FilterAppliedEvent,
  GovernanceViewedEvent,
  PageViewEvent,
  SearchQueryEvent,
  SpecDownloadEvent,
  UserSessionEvent,
} from '../../src/models/analytics-event.js';

// ---------------------------------------------------------------------------
// Type guard helpers (compile-time tests via type assertion)
// ---------------------------------------------------------------------------

function assertType<T>(_value: T): void {
  // No-op — used to assert a value satisfies a TypeScript type at compile time.
}

describe('AnalyticsEvent type safety', () => {
  it('accepts a valid PageViewEvent', () => {
    const event: PageViewEvent = { type: 'page_view', page: '/catalog', duration: 5000 };
    assertType<AnalyticsEvent>(event);
    expect(event.type).toBe('page_view');
    expect(event.page).toBe('/catalog');
    expect(event.duration).toBe(5000);
  });

  it('accepts a PageViewEvent without optional duration', () => {
    const event: PageViewEvent = { type: 'page_view', page: '/search' };
    assertType<AnalyticsEvent>(event);
    expect(event.duration).toBeUndefined();
  });

  it('accepts a valid SearchQueryEvent', () => {
    const event: SearchQueryEvent = {
      type: 'search_query',
      queryHash: 'abc123',
      queryLength: 10,
      resultCount: 5,
      clickedResult: 'payments-api',
    };
    assertType<AnalyticsEvent>(event);
    expect(event.queryHash).toBe('abc123');
    expect(event.resultCount).toBe(5);
  });

  it('accepts a SearchQueryEvent without optional clickedResult', () => {
    const event: SearchQueryEvent = {
      type: 'search_query',
      queryHash: 'xyz',
      queryLength: 3,
      resultCount: 0,
    };
    assertType<AnalyticsEvent>(event);
    expect(event.clickedResult).toBeUndefined();
  });

  it('accepts a valid ApiViewEvent', () => {
    const event: ApiViewEvent = { type: 'api_view', apiId: 'my-api', source: 'search' };
    assertType<AnalyticsEvent>(event);
    expect(event.apiId).toBe('my-api');
    expect(event.source).toBe('search');
  });

  it('accepts all ApiViewEvent source values', () => {
    const sources: ApiViewEvent['source'][] = ['catalog', 'search', 'chat', 'compare'];
    sources.forEach((source) => {
      const event: ApiViewEvent = { type: 'api_view', apiId: 'api', source };
      assertType<AnalyticsEvent>(event);
      expect(event.source).toBe(source);
    });
  });

  it('accepts a valid SpecDownloadEvent', () => {
    const event: SpecDownloadEvent = { type: 'spec_download', apiId: 'my-api', format: 'yaml' };
    assertType<AnalyticsEvent>(event);
    expect(event.format).toBe('yaml');
  });

  it('accepts a valid ChatInteractionEvent', () => {
    const event: ChatInteractionEvent = {
      type: 'chat_interaction',
      sessionId: 'sess-1',
      messageCount: 5,
      agentUsed: 'api-discovery',
    };
    assertType<AnalyticsEvent>(event);
    expect(event.messageCount).toBe(5);
  });

  it('accepts a valid ComparisonMadeEvent', () => {
    const event: ComparisonMadeEvent = {
      type: 'comparison_made',
      apiIds: ['api-1', 'api-2'],
      usedAiAnalysis: true,
    };
    assertType<AnalyticsEvent>(event);
    expect(event.apiIds).toHaveLength(2);
  });

  it('accepts a valid GovernanceViewedEvent', () => {
    const event: GovernanceViewedEvent = {
      type: 'governance_viewed',
      section: 'security',
    };
    assertType<AnalyticsEvent>(event);
    expect(event.apiId).toBeUndefined();
  });

  it('accepts a valid FilterAppliedEvent', () => {
    const event: FilterAppliedEvent = {
      type: 'filter_applied',
      filterType: 'tag',
      filterValue: 'payments',
      context: 'catalog',
    };
    assertType<AnalyticsEvent>(event);
    expect(event.context).toBe('catalog');
  });

  it('accepts a valid UserSessionEvent', () => {
    const event: UserSessionEvent = {
      type: 'user_session',
      userIdHash: 'abc123def456',
      sessionDuration: 300,
      pagesVisited: 5,
    };
    assertType<AnalyticsEvent>(event);
    expect(event.sessionDuration).toBe(300);
  });
});

// ---------------------------------------------------------------------------
// AnalyticsEventEnvelope
// ---------------------------------------------------------------------------

describe('AnalyticsEventEnvelope', () => {
  it('wraps an event with client metadata', () => {
    const envelope: AnalyticsEventEnvelope = {
      event: { type: 'page_view', page: '/catalog' },
      clientTimestamp: '2026-04-21T12:00:00Z',
      pagePath: '/catalog',
      sessionId: 'sess-abc',
    };
    expect(envelope.event.type).toBe('page_view');
    expect(envelope.clientTimestamp).toBe('2026-04-21T12:00:00Z');
    expect(envelope.sessionId).toBe('sess-abc');
  });

  it('accepts an envelope without optional sessionId', () => {
    const envelope: AnalyticsEventEnvelope = {
      event: { type: 'page_view', page: '/search' },
      clientTimestamp: '2026-04-21T12:00:00Z',
      pagePath: '/search',
    };
    expect(envelope.sessionId).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// AnalyticsEventBatch
// ---------------------------------------------------------------------------

describe('AnalyticsEventBatch', () => {
  it('holds an array of event envelopes', () => {
    const batch: AnalyticsEventBatch = {
      events: [
        {
          event: { type: 'page_view', page: '/catalog' },
          clientTimestamp: '2026-04-21T12:00:00Z',
          pagePath: '/catalog',
        },
        {
          event: { type: 'api_view', apiId: 'payments', source: 'catalog' },
          clientTimestamp: '2026-04-21T12:00:01Z',
          pagePath: '/api/payments',
        },
      ],
    };
    expect(batch.events).toHaveLength(2);
    expect(batch.events[0].event.type).toBe('page_view');
    expect(batch.events[1].event.type).toBe('api_view');
  });

  it('accepts an empty events array', () => {
    const batch: AnalyticsEventBatch = { events: [] };
    expect(batch.events).toHaveLength(0);
  });
});
