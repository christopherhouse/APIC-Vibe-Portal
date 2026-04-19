/**
 * Tests for app-insights-browser.ts and track-events.ts telemetry helpers.
 *
 * Uses the Jest mock for @microsoft/applicationinsights-web so no real
 * network calls are made and no browser globals are required.
 */

// Reset module registry between tests so the singleton is fresh
beforeEach(() => {
  jest.resetModules();
  jest.clearAllMocks();
});

describe('getAppInsights / initAppInsights', () => {
  it('returns null before initAppInsights is called', async () => {
    const { getAppInsights } = await import('../app-insights-browser');
    expect(getAppInsights()).toBeNull();
  });

  it('returns null when initAppInsights is called with an empty string', async () => {
    const { getAppInsights, initAppInsights } = await import('../app-insights-browser');
    initAppInsights('');
    expect(getAppInsights()).toBeNull();
  });

  it('creates and returns an ApplicationInsights instance when a connection string is provided', async () => {
    const { getAppInsights, initAppInsights } = await import('../app-insights-browser');
    initAppInsights('InstrumentationKey=test-key');
    const ai = getAppInsights();
    expect(ai).not.toBeNull();
    expect(ai!.loadAppInsights).toBeDefined();
  });

  it('calls loadAppInsights on init but does NOT call trackPageView', async () => {
    const { getAppInsights, initAppInsights } = await import('../app-insights-browser');
    initAppInsights('InstrumentationKey=test-key');
    const ai = getAppInsights()!;
    expect(ai.loadAppInsights).toHaveBeenCalledTimes(1);
    // trackPageView is handled by enableAutoRouteTracking — not called manually
    expect(ai.trackPageView).not.toHaveBeenCalled();
  });

  it('is idempotent — second initAppInsights call is a no-op', async () => {
    const { getAppInsights, initAppInsights } = await import('../app-insights-browser');
    initAppInsights('InstrumentationKey=test-key');
    initAppInsights('InstrumentationKey=other-key');
    const ai = getAppInsights()!;
    // loadAppInsights should only be called once (idempotent)
    expect(ai.loadAppInsights).toHaveBeenCalledTimes(1);
  });

  it('returns the same instance on subsequent getAppInsights calls', async () => {
    const { getAppInsights, initAppInsights } = await import('../app-insights-browser');
    initAppInsights('InstrumentationKey=test-key');
    const ai1 = getAppInsights();
    const ai2 = getAppInsights();
    expect(ai1).toBe(ai2);
  });
});

describe('track-events', () => {
  it('trackSearchPerformed calls trackEvent with correct name and properties', async () => {
    const { getAppInsights, initAppInsights } = await import('../app-insights-browser');
    initAppInsights('InstrumentationKey=test-key');
    const { trackSearchPerformed } = await import('../track-events');
    const ai = getAppInsights()!;

    trackSearchPerformed({ query: 'test', resultCount: 5, durationMs: 120 });

    expect(ai.trackEvent).toHaveBeenCalledWith({
      name: 'search_performed',
      properties: { query: 'test', resultCount: 5, durationMs: 120 },
    });
  });

  it('trackApiViewed calls trackEvent with apiId and source', async () => {
    const { getAppInsights, initAppInsights } = await import('../app-insights-browser');
    initAppInsights('InstrumentationKey=test-key');
    const { trackApiViewed } = await import('../track-events');
    const ai = getAppInsights()!;

    trackApiViewed({ apiId: 'api-123', source: 'search' });

    expect(ai.trackEvent).toHaveBeenCalledWith({
      name: 'api_viewed',
      properties: { apiId: 'api-123', source: 'search' },
    });
  });

  it('trackChatMessageSent calls trackEvent', async () => {
    const { getAppInsights, initAppInsights } = await import('../app-insights-browser');
    initAppInsights('InstrumentationKey=test-key');
    const { trackChatMessageSent } = await import('../track-events');
    const ai = getAppInsights()!;

    trackChatMessageSent({ messageLength: 42, sessionId: 'sess-1' });

    expect(ai.trackEvent).toHaveBeenCalledWith({
      name: 'chat_message_sent',
      properties: { messageLength: 42, sessionId: 'sess-1' },
    });
  });

  it('trackFilterApplied calls trackEvent', async () => {
    const { getAppInsights, initAppInsights } = await import('../app-insights-browser');
    initAppInsights('InstrumentationKey=test-key');
    const { trackFilterApplied } = await import('../track-events');
    const ai = getAppInsights()!;

    trackFilterApplied({ filterType: 'tag', filterValue: 'payments' });

    expect(ai.trackEvent).toHaveBeenCalledWith({
      name: 'filter_applied',
      properties: { filterType: 'tag', filterValue: 'payments' },
    });
  });

  it('trackSpecDownloaded calls trackEvent', async () => {
    const { getAppInsights, initAppInsights } = await import('../app-insights-browser');
    initAppInsights('InstrumentationKey=test-key');
    const { trackSpecDownloaded } = await import('../track-events');
    const ai = getAppInsights()!;

    trackSpecDownloaded({ apiId: 'api-456', format: 'openapi' });

    expect(ai.trackEvent).toHaveBeenCalledWith({
      name: 'spec_downloaded',
      properties: { apiId: 'api-456', format: 'openapi' },
    });
  });

  it('trackError calls trackException', async () => {
    const { getAppInsights, initAppInsights } = await import('../app-insights-browser');
    initAppInsights('InstrumentationKey=test-key');
    const { trackError } = await import('../track-events');
    const ai = getAppInsights()!;
    const err = new Error('boom');

    trackError(err, { component: 'ChatPanel' });

    expect(ai.trackException).toHaveBeenCalledWith({
      exception: err,
      properties: { component: 'ChatPanel' },
    });
  });

  it('track functions are no-ops when App Insights is not initialized', async () => {
    // Do NOT call initAppInsights — SDK should stay dormant
    const { trackSearchPerformed } = await import('../track-events');

    // Should not throw
    expect(() =>
      trackSearchPerformed({ query: 'test', resultCount: 0, durationMs: 0 }),
    ).not.toThrow();
  });
});

