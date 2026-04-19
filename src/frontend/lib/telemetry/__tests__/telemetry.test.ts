/**
 * Tests for track-events.ts telemetry helpers.
 *
 * Uses the Jest mock for @microsoft/applicationinsights-web so no real
 * network calls are made and no browser globals are required.
 */

// Reset module registry between tests so the singleton is fresh
beforeEach(() => {
  jest.resetModules();
  jest.clearAllMocks();
});

function setEnv(value: string | undefined) {
  Object.defineProperty(process.env, 'NEXT_PUBLIC_APPLICATIONINSIGHTS_CONNECTION_STRING', {
    value,
    writable: true,
    configurable: true,
  });
}

describe('getAppInsights', () => {
  it('returns null when connection string is not set', async () => {
    setEnv(undefined);
    const { getAppInsights } = await import('../app-insights-browser');
    expect(getAppInsights()).toBeNull();
  });

  it('creates and returns an ApplicationInsights instance when connection string is set', async () => {
    setEnv('InstrumentationKey=test-key');
    const { getAppInsights } = await import('../app-insights-browser');
    const ai = getAppInsights();
    expect(ai).not.toBeNull();
    expect(ai!.loadAppInsights).toBeDefined();
  });

  it('calls loadAppInsights and trackPageView on init', async () => {
    setEnv('InstrumentationKey=test-key');
    const { getAppInsights } = await import('../app-insights-browser');
    const ai = getAppInsights()!;
    expect(ai.loadAppInsights).toHaveBeenCalledTimes(1);
    expect(ai.trackPageView).toHaveBeenCalledTimes(1);
  });

  it('returns the same instance on subsequent calls', async () => {
    setEnv('InstrumentationKey=test-key');
    const { getAppInsights } = await import('../app-insights-browser');
    const ai1 = getAppInsights();
    const ai2 = getAppInsights();
    expect(ai1).toBe(ai2);
    // loadAppInsights should only be called once (not twice)
    expect(ai1!.loadAppInsights).toHaveBeenCalledTimes(1);
  });
});

describe('track-events', () => {
  it('trackSearchPerformed calls trackEvent with correct name and properties', async () => {
    setEnv('InstrumentationKey=test-key');
    const { getAppInsights } = await import('../app-insights-browser');
    const { trackSearchPerformed } = await import('../track-events');
    const ai = getAppInsights()!;

    trackSearchPerformed({ query: 'test', resultCount: 5, durationMs: 120 });

    expect(ai.trackEvent).toHaveBeenCalledWith({
      name: 'search_performed',
      properties: { query: 'test', resultCount: 5, durationMs: 120 },
    });
  });

  it('trackApiViewed calls trackEvent with apiId and source', async () => {
    setEnv('InstrumentationKey=test-key');
    const { getAppInsights } = await import('../app-insights-browser');
    const { trackApiViewed } = await import('../track-events');
    const ai = getAppInsights()!;

    trackApiViewed({ apiId: 'api-123', source: 'search' });

    expect(ai.trackEvent).toHaveBeenCalledWith({
      name: 'api_viewed',
      properties: { apiId: 'api-123', source: 'search' },
    });
  });

  it('trackChatMessageSent calls trackEvent', async () => {
    setEnv('InstrumentationKey=test-key');
    const { getAppInsights } = await import('../app-insights-browser');
    const { trackChatMessageSent } = await import('../track-events');
    const ai = getAppInsights()!;

    trackChatMessageSent({ messageLength: 42, sessionId: 'sess-1' });

    expect(ai.trackEvent).toHaveBeenCalledWith({
      name: 'chat_message_sent',
      properties: { messageLength: 42, sessionId: 'sess-1' },
    });
  });

  it('trackFilterApplied calls trackEvent', async () => {
    setEnv('InstrumentationKey=test-key');
    const { getAppInsights } = await import('../app-insights-browser');
    const { trackFilterApplied } = await import('../track-events');
    const ai = getAppInsights()!;

    trackFilterApplied({ filterType: 'tag', filterValue: 'payments' });

    expect(ai.trackEvent).toHaveBeenCalledWith({
      name: 'filter_applied',
      properties: { filterType: 'tag', filterValue: 'payments' },
    });
  });

  it('trackSpecDownloaded calls trackEvent', async () => {
    setEnv('InstrumentationKey=test-key');
    const { getAppInsights } = await import('../app-insights-browser');
    const { trackSpecDownloaded } = await import('../track-events');
    const ai = getAppInsights()!;

    trackSpecDownloaded({ apiId: 'api-456', format: 'openapi' });

    expect(ai.trackEvent).toHaveBeenCalledWith({
      name: 'spec_downloaded',
      properties: { apiId: 'api-456', format: 'openapi' },
    });
  });

  it('trackError calls trackException', async () => {
    setEnv('InstrumentationKey=test-key');
    const { getAppInsights } = await import('../app-insights-browser');
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
    setEnv(undefined);
    const { trackSearchPerformed } = await import('../track-events');

    // Should not throw
    expect(() =>
      trackSearchPerformed({ query: 'test', resultCount: 0, durationMs: 0 }),
    ).not.toThrow();
  });
});

