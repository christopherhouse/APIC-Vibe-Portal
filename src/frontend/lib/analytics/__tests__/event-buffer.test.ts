/**
 * Tests for the client-side analytics EventBuffer.
 */

import { EventBuffer, isDoNotTrackEnabled } from '../event-buffer';
import type { AnalyticsEventEnvelope } from '@apic-vibe-portal/shared';

// Mock @/lib/api-client so we don't pull in MSAL/browser globals
jest.mock('@/lib/api-client', () => ({
  getAuthToken: jest.fn().mockResolvedValue(undefined),
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeEnvelope(page = '/catalog'): AnalyticsEventEnvelope {
  return {
    event: { type: 'page_view', page },
    clientTimestamp: new Date().toISOString(),
    pagePath: page,
    sessionId: 'test-session',
  };
}

function makeFetch(status = 202, body = { accepted: 1 }): jest.MockedFunction<typeof fetch> {
  return jest.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: jest.fn().mockResolvedValue(body),
  } as unknown as Response);
}

/** Flush the microtask queue to allow chained promises to resolve. */
async function flushPromises(): Promise<void> {
  for (let i = 0; i < 10; i++) {
    await Promise.resolve();
  }
}

// ---------------------------------------------------------------------------
// isDoNotTrackEnabled
// ---------------------------------------------------------------------------

describe('isDoNotTrackEnabled', () => {
  const originalDnt = navigator.doNotTrack;

  afterEach(() => {
    Object.defineProperty(navigator, 'doNotTrack', {
      value: originalDnt,
      configurable: true,
    });
  });

  it('returns false when doNotTrack is null', () => {
    Object.defineProperty(navigator, 'doNotTrack', { value: null, configurable: true });
    expect(isDoNotTrackEnabled()).toBe(false);
  });

  it('returns true when doNotTrack is "1"', () => {
    Object.defineProperty(navigator, 'doNotTrack', { value: '1', configurable: true });
    expect(isDoNotTrackEnabled()).toBe(true);
  });

  it('returns false when doNotTrack is "0"', () => {
    Object.defineProperty(navigator, 'doNotTrack', { value: '0', configurable: true });
    expect(isDoNotTrackEnabled()).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// EventBuffer — push and size
// ---------------------------------------------------------------------------

describe('EventBuffer', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    // Ensure DNT is off for buffer tests
    Object.defineProperty(navigator, 'doNotTrack', { value: null, configurable: true });
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('starts empty', () => {
    const buf = new EventBuffer({ fetchFn: makeFetch() });
    expect(buf.size).toBe(0);
    buf.destroy();
  });

  it('push increments size', () => {
    const buf = new EventBuffer({ fetchFn: makeFetch() });
    buf.push(makeEnvelope());
    expect(buf.size).toBe(1);
    buf.destroy();
  });

  it('does not add events when DNT is enabled', () => {
    Object.defineProperty(navigator, 'doNotTrack', { value: '1', configurable: true });
    const buf = new EventBuffer({ fetchFn: makeFetch() });
    buf.push(makeEnvelope());
    expect(buf.size).toBe(0);
    buf.destroy();
  });

  it('auto-flushes when maxSize is reached', async () => {
    const fetchFn = makeFetch();
    const buf = new EventBuffer({ maxSize: 3, fetchFn });
    buf.push(makeEnvelope('/a'));
    buf.push(makeEnvelope('/b'));
    buf.push(makeEnvelope('/c')); // triggers flush

    await flushPromises();

    expect(fetchFn).toHaveBeenCalledTimes(1);
    expect(buf.size).toBe(0);
    buf.destroy();
  });

  it('auto-flushes on interval', async () => {
    const fetchFn = makeFetch();
    const buf = new EventBuffer({ flushIntervalMs: 500, fetchFn });
    buf.push(makeEnvelope());

    jest.advanceTimersByTime(500);
    await flushPromises();

    expect(fetchFn).toHaveBeenCalledTimes(1);
    buf.destroy();
  });

  it('does not flush when queue is empty', async () => {
    const fetchFn = makeFetch();
    const buf = new EventBuffer({ fetchFn });
    await buf.flush();
    expect(fetchFn).not.toHaveBeenCalled();
    buf.destroy();
  });

  it('calls onFlush callback with accepted count on success', async () => {
    const fetchFn = makeFetch(202, { accepted: 2 });
    const buf = new EventBuffer({ maxSize: 100, fetchFn });
    const onFlush = jest.fn();
    buf.onFlush(onFlush);

    buf.push(makeEnvelope());
    buf.push(makeEnvelope());
    await buf.flush();
    await flushPromises();

    expect(onFlush).toHaveBeenCalledWith(2, undefined);
    buf.destroy();
  });

  it('calls onFlush callback with error on HTTP failure', async () => {
    const fetchFn = makeFetch(500, {});
    const buf = new EventBuffer({ maxSize: 100, fetchFn });
    const onFlush = jest.fn();
    buf.onFlush(onFlush);

    buf.push(makeEnvelope());
    await buf.flush();
    await flushPromises();

    expect(onFlush).toHaveBeenCalledWith(0, expect.any(Error));
    buf.destroy();
  });

  it('calls onFlush callback with error when fetch throws', async () => {
    const fetchFn = jest.fn().mockRejectedValue(new Error('Network error'));
    const buf = new EventBuffer({
      maxSize: 100,
      fetchFn: fetchFn as unknown as typeof fetch,
    });
    const onFlush = jest.fn();
    buf.onFlush(onFlush);

    buf.push(makeEnvelope());
    await buf.flush();
    await flushPromises();

    expect(onFlush).toHaveBeenCalledWith(0, expect.any(Error));
    buf.destroy();
  });

  it('destroy stops the interval timer', async () => {
    const fetchFn = makeFetch();
    const buf = new EventBuffer({ flushIntervalMs: 100, fetchFn });
    buf.push(makeEnvelope());
    buf.destroy();

    jest.advanceTimersByTime(200);
    await flushPromises();

    // Timer was destroyed so no automatic flush
    expect(fetchFn).not.toHaveBeenCalled();
  });

  it('sends the correct endpoint', async () => {
    const fetchFn = makeFetch();
    const buf = new EventBuffer({ endpoint: '/custom/events', maxSize: 1, fetchFn });
    buf.push(makeEnvelope());
    await flushPromises();

    expect(fetchFn).toHaveBeenCalledWith(
      '/custom/events',
      expect.objectContaining({ method: 'POST' })
    );
    buf.destroy();
  });
});
