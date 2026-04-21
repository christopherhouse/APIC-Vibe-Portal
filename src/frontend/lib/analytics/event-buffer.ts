/**
 * Client-side analytics event buffer.
 *
 * Collects events locally and flushes them to the BFF in batches.
 * The buffer flushes automatically when:
 *   - It reaches `maxSize` events (default: 10)
 *   - The flush interval elapses (default: 30 seconds)
 *   - `flush()` is called manually (e.g. on page unload)
 *
 * If Do Not Track is enabled in the browser, all tracking operations are
 * silently suppressed and the buffer remains permanently empty.
 */

import type { AnalyticsEventEnvelope } from '@apic-vibe-portal/shared';

/** Configuration options for the event buffer. */
export interface EventBufferOptions {
  /** Maximum number of events to buffer before flushing (default: 10). */
  maxSize?: number;
  /** Flush interval in milliseconds (default: 30 000). */
  flushIntervalMs?: number;
  /** Endpoint to POST event batches to (default: "/api/analytics/events"). */
  endpoint?: string;
  /** Factory for fetch — injectable for testing. */
  fetchFn?: typeof fetch;
}

/** Callback invoked when a flush attempt completes. */
export type FlushCallback = (accepted: number, error?: Error) => void;

const DEFAULT_MAX_SIZE = 10;
const DEFAULT_FLUSH_INTERVAL_MS = 30_000;
const DEFAULT_ENDPOINT = '/api/analytics/events';

/**
 * Returns `true` when the browser's Do Not Track preference is active.
 *
 * Checks both `navigator.doNotTrack` (modern) and `window.doNotTrack`
 * (legacy IE/Edge).
 */
export function isDoNotTrackEnabled(): boolean {
  if (typeof navigator === 'undefined') return false;
  const dnt =
    navigator.doNotTrack ??
    (typeof window !== 'undefined'
      ? (window as Window & { doNotTrack?: string }).doNotTrack
      : null);
  return dnt === '1' || dnt === 'yes';
}

/** Acquire a MSAL access token for the BFF if available.  Returns `undefined` when no account is active. */
async function _getToken(): Promise<string | undefined> {
  try {
    // Static import path — Jest mock intercepts this correctly.
    // The cast avoids bundler issues in environments where the module is not available.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const mod: any = await import('@/lib/api-client');
    return typeof mod.getAuthToken === 'function' ? await mod.getAuthToken() : undefined;
  } catch {
    return undefined;
  }
}

/**
 * Client-side analytics event buffer.
 *
 * Instantiate once per application (typically inside `AnalyticsProvider`) and
 * call `destroy()` when the component unmounts to cancel the flush timer.
 */
export class EventBuffer {
  private _queue: AnalyticsEventEnvelope[] = [];
  private _timer: ReturnType<typeof setInterval> | null = null;
  private readonly _maxSize: number;
  private readonly _flushIntervalMs: number;
  private readonly _endpoint: string;
  private readonly _fetchFn: typeof fetch;
  private _onFlush: FlushCallback | null = null;

  constructor(options: EventBufferOptions = {}) {
    this._maxSize = options.maxSize ?? DEFAULT_MAX_SIZE;
    this._flushIntervalMs = options.flushIntervalMs ?? DEFAULT_FLUSH_INTERVAL_MS;
    this._endpoint = options.endpoint ?? DEFAULT_ENDPOINT;
    this._fetchFn =
      options.fetchFn ?? (typeof fetch !== 'undefined' ? fetch.bind(globalThis) : _noop);

    this._startTimer();
  }

  /** Register a callback that is invoked after every flush attempt. */
  onFlush(cb: FlushCallback): void {
    this._onFlush = cb;
  }

  /**
   * Add an event to the buffer.
   *
   * When Do Not Track is active the event is silently dropped and no flush is
   * triggered.  When the buffer reaches `maxSize` a flush is triggered
   * automatically.
   */
  push(envelope: AnalyticsEventEnvelope): void {
    if (isDoNotTrackEnabled()) return;
    this._queue.push(envelope);
    if (this._queue.length >= this._maxSize) {
      void this.flush();
    }
  }

  /**
   * Flush all buffered events to the BFF.
   *
   * This is a no-op when the queue is empty.  The method is intentionally
   * non-throwing: network errors are caught and surfaced through the
   * `onFlush` callback.
   */
  async flush(): Promise<void> {
    if (this._queue.length === 0) return;

    const batch = this._queue.splice(0);
    try {
      const token = await _getToken();
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const res = await this._fetchFn(this._endpoint, {
        method: 'POST',
        headers,
        body: JSON.stringify({ events: batch }),
        // keepalive allows the request to outlive the page (unload scenario)
        keepalive: true,
      });

      if (res.ok) {
        if (res.status === 204) {
          // No-content response — treat as full acceptance.
          this._onFlush?.(batch.length, undefined);
        } else {
          let accepted = batch.length;
          try {
            const data = (await res.json()) as { accepted?: number };
            accepted = data.accepted ?? batch.length;
          } catch {
            // Non-JSON body — fall back to batch length.
          }
          this._onFlush?.(accepted, undefined);
        }
      } else {
        this._onFlush?.(0, new Error(`HTTP ${res.status}`));
      }
    } catch (err) {
      this._onFlush?.(0, err instanceof Error ? err : new Error(String(err)));
    }
  }

  /** Cancel the periodic flush timer and release resources. */
  destroy(): void {
    if (this._timer !== null) {
      clearInterval(this._timer);
      this._timer = null;
    }
  }

  /** Current number of buffered events. */
  get size(): number {
    return this._queue.length;
  }

  private _startTimer(): void {
    if (typeof setInterval === 'undefined') return;
    this._timer = setInterval(() => {
      void this.flush();
    }, this._flushIntervalMs);
  }
}

function _noop(): Promise<Response> {
  return Promise.resolve(new Response(null, { status: 204 }));
}
