/**
 * Unit tests for the chat-api SSE stream parser.
 *
 * These tests mock `fetch` and `getAuthToken` so they run without a real BFF
 * and without MSAL, focusing purely on the SSE parsing behaviour.
 *
 * @jest-environment node
 */

import { streamChatMessage } from '@/lib/chat-api';

// ─── helpers ────────────────────────────────────────────────────────────────

/** Build a ReadableStream from an array of SSE string chunks. */
function makeStream(...chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    },
  });
}

/** Wrap SSE event objects into a single-chunk stream. */
function sseStream(...events: object[]): ReadableStream<Uint8Array> {
  const body = events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join('');
  return makeStream(body);
}

// ─── mocks ──────────────────────────────────────────────────────────────────

// Mock getAuthToken so tests don't need MSAL
jest.mock('@/lib/api-client', () => ({
  getAuthToken: jest.fn().mockResolvedValue(undefined),
}));

const mockFetch = jest.fn<Promise<Response>, [RequestInfo | URL, RequestInit?]>();

beforeEach(() => {
  global.fetch = mockFetch;
  mockFetch.mockReset();
});

function mockOkResponse(stream: ReadableStream<Uint8Array>) {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    status: 200,
    body: stream,
  } as unknown as Response);
}

function mockErrorResponse(status: number) {
  mockFetch.mockResolvedValueOnce({
    ok: false,
    status,
    statusText: 'Error',
    body: null,
  } as unknown as Response);
}

// ─── tests ───────────────────────────────────────────────────────────────────

const NOW = '2026-04-19T00:00:00.000Z';

const FINAL_MSG = {
  id: 'msg-1',
  role: 'assistant' as const,
  content: 'Hello world',
  citations: null,
  timestamp: NOW,
};

describe('streamChatMessage — happy path', () => {
  it('calls the BFF stream endpoint with correct body', async () => {
    mockOkResponse(
      sseStream(
        { type: 'start', sessionId: 's1' },
        { type: 'content', content: 'Hello ' },
        { type: 'content', content: 'world' },
        { type: 'end', message: FINAL_MSG, sessionId: 's1' }
      )
    );

    const onToken = jest.fn();
    await streamChatMessage({ message: 'Hi', sessionId: 'prev', onToken });

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/chat/stream',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ message: 'Hi', sessionId: 'prev' }),
      })
    );
  });

  it('invokes onStart with the session ID from the start event', async () => {
    mockOkResponse(
      sseStream(
        { type: 'start', sessionId: 's1' },
        { type: 'end', message: FINAL_MSG, sessionId: 's1' }
      )
    );

    const onStart = jest.fn();
    await streamChatMessage({ message: 'Hi', onToken: jest.fn(), onStart });
    expect(onStart).toHaveBeenCalledWith('s1');
  });

  it('collects all content tokens in order', async () => {
    mockOkResponse(
      sseStream(
        { type: 'start', sessionId: 's1' },
        { type: 'content', content: 'foo' },
        { type: 'content', content: 'bar' },
        { type: 'content', content: 'baz' },
        { type: 'end', message: FINAL_MSG, sessionId: 's1' }
      )
    );

    const tokens: string[] = [];
    await streamChatMessage({ message: 'Hi', onToken: (t) => tokens.push(t) });
    expect(tokens).toEqual(['foo', 'bar', 'baz']);
  });

  it('returns the final message and session ID', async () => {
    mockOkResponse(
      sseStream(
        { type: 'start', sessionId: 's1' },
        { type: 'end', message: FINAL_MSG, sessionId: 's1' }
      )
    );

    const result = await streamChatMessage({ message: 'Hi', onToken: jest.fn() });
    expect(result.sessionId).toBe('s1');
    expect(result.message.content).toBe('Hello world');
  });

  it('normalizes citations: null → undefined in the final message', async () => {
    mockOkResponse(
      sseStream(
        { type: 'start', sessionId: 's1' },
        { type: 'end', message: { ...FINAL_MSG, citations: null }, sessionId: 's1' }
      )
    );

    const result = await streamChatMessage({ message: 'Hi', onToken: jest.fn() });
    expect(result.message.citations).toBeUndefined();
  });

  it('preserves citations array when present', async () => {
    const citations = [{ title: 'Test API', url: '/catalog/test' }];
    mockOkResponse(
      sseStream(
        { type: 'start', sessionId: 's1' },
        { type: 'end', message: { ...FINAL_MSG, citations }, sessionId: 's1' }
      )
    );

    const result = await streamChatMessage({ message: 'Hi', onToken: jest.fn() });
    expect(result.message.citations).toEqual(citations);
  });

  it('handles multi-chunk delivery (partial SSE events split across reads)', async () => {
    const fullEvent =
      `data: ${JSON.stringify({ type: 'start', sessionId: 's2' })}\n\n` +
      `data: ${JSON.stringify({ type: 'end', message: FINAL_MSG, sessionId: 's2' })}\n\n`;

    // Split at an arbitrary mid-event boundary
    const half = Math.floor(fullEvent.length / 2);
    const stream = makeStream(fullEvent.slice(0, half), fullEvent.slice(half));
    mockOkResponse(stream);

    const result = await streamChatMessage({ message: 'Hi', onToken: jest.fn() });
    expect(result.sessionId).toBe('s2');
  });

  it('skips malformed (non-JSON) data lines without throwing', async () => {
    const body =
      `data: not-valid-json\n\n` +
      `data: ${JSON.stringify({ type: 'start', sessionId: 's3' })}\n\n` +
      `data: ${JSON.stringify({ type: 'end', message: FINAL_MSG, sessionId: 's3' })}\n\n`;
    mockOkResponse(makeStream(body));

    const result = await streamChatMessage({ message: 'Hi', onToken: jest.fn() });
    expect(result.sessionId).toBe('s3');
  });
});

describe('streamChatMessage — error handling', () => {
  it('throws when the HTTP response is not ok', async () => {
    mockErrorResponse(401);
    await expect(streamChatMessage({ message: 'Hi', onToken: jest.fn() })).rejects.toThrow(
      'Chat request failed: 401'
    );
  });

  it('throws when stream ends without a final end event', async () => {
    mockOkResponse(
      sseStream(
        { type: 'start', sessionId: 's1' },
        { type: 'content', content: 'partial…' }
        // no 'end' event
      )
    );

    await expect(streamChatMessage({ message: 'Hi', onToken: jest.fn() })).rejects.toThrow(
      'Stream ended without a final message'
    );
  });

  it('throws the error message from a typed error event', async () => {
    mockOkResponse(
      sseStream(
        { type: 'start', sessionId: 's1' },
        { type: 'error', error: 'Internal server error', sessionId: 's1' }
      )
    );

    await expect(streamChatMessage({ message: 'Hi', onToken: jest.fn() })).rejects.toThrow(
      'Internal server error'
    );
  });

  it('handles BFF rate-limit payload without a type field', async () => {
    // The BFF rate-limit path emits {"error":"Rate limit exceeded","sessionId":"..."}
    mockOkResponse(sseStream({ error: 'Rate limit exceeded', sessionId: 's1' }));

    await expect(streamChatMessage({ message: 'Hi', onToken: jest.fn() })).rejects.toThrow(
      'Rate limit exceeded'
    );
  });

  it('throws on abort signal', async () => {
    const controller = new AbortController();
    mockFetch.mockRejectedValueOnce(Object.assign(new Error('AbortError'), { name: 'AbortError' }));
    controller.abort();

    await expect(
      streamChatMessage({ message: 'Hi', onToken: jest.fn(), signal: controller.signal })
    ).rejects.toMatchObject({ name: 'AbortError' });
  });
});
