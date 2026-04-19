/**
 * Chat API helper functions.
 *
 * Provides typed access to the BFF chat endpoints:
 *   POST /api/chat/stream  — streaming SSE chat
 *   GET  /api/chat/history — fetch conversation history
 *   DELETE /api/chat/history — clear conversation history
 */

import type { ChatMessage } from '@apic-vibe-portal/shared';
import { getMsalInstance } from '@/lib/auth/auth-provider';
import { getBffApiScope } from '@/lib/auth/msal-config';

/** SSE event types emitted by the BFF streaming endpoint. */
export type ChatStreamEventType = 'start' | 'content' | 'end' | 'error';

export interface ChatStreamStartEvent {
  type: 'start';
  sessionId: string;
}

export interface ChatStreamContentEvent {
  type: 'content';
  content: string;
}

export interface ChatStreamEndEvent {
  type: 'end';
  message: ChatMessage;
  sessionId: string;
}

export interface ChatStreamErrorEvent {
  type: 'error';
  error: string;
  sessionId?: string;
}

export type ChatStreamEvent =
  | ChatStreamStartEvent
  | ChatStreamContentEvent
  | ChatStreamEndEvent
  | ChatStreamErrorEvent;

/** Acquire an access token for BFF requests. */
async function getAuthToken(): Promise<string | undefined> {
  try {
    const msalInstance = getMsalInstance();
    const account = msalInstance.getActiveAccount();
    if (!account) return undefined;
    const bffApiScope = getBffApiScope();
    const result = await msalInstance.acquireTokenSilent({
      scopes: bffApiScope ? [bffApiScope] : ['openid', 'profile', 'email'],
      account,
    });
    return result.accessToken;
  } catch {
    return undefined;
  }
}

/** Build auth headers for BFF requests. */
async function buildAuthHeaders(): Promise<Record<string, string>> {
  const token = await getAuthToken();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

/**
 * Stream a chat message to the BFF SSE endpoint.
 *
 * Calls the provided callbacks as SSE events arrive.
 * Returns the final assistant ChatMessage when the stream completes.
 */
export async function streamChatMessage(options: {
  message: string;
  sessionId?: string | null;
  onToken: (token: string) => void;
  onStart?: (sessionId: string) => void;
  signal?: AbortSignal;
}): Promise<{ message: ChatMessage; sessionId: string }> {
  const { message, sessionId, onToken, onStart, signal } = options;

  const headers = await buildAuthHeaders();

  const response = await fetch('/api/chat/stream', {
    method: 'POST',
    headers,
    body: JSON.stringify({ message, sessionId: sessionId ?? undefined }),
    signal,
  });

  if (!response.ok) {
    throw new Error(`Chat request failed: ${response.status} ${response.statusText}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('Response body is not readable');
  }

  const decoder = new TextDecoder();
  let buffer = '';
  let finalMessage: ChatMessage | null = null;
  let finalSessionId: string = sessionId ?? '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Process complete SSE events (separated by \n\n)
      const parts = buffer.split('\n\n');
      buffer = parts.pop() ?? '';

      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith('data: ')) continue;

        const dataStr = line.slice(6);
        let event: ChatStreamEvent;
        try {
          event = JSON.parse(dataStr) as ChatStreamEvent;
        } catch {
          continue;
        }

        if (event.type === 'start') {
          finalSessionId = event.sessionId;
          onStart?.(event.sessionId);
        } else if (event.type === 'content') {
          onToken(event.content);
        } else if (event.type === 'end') {
          finalMessage = event.message;
          finalSessionId = event.sessionId;
        } else if (event.type === 'error') {
          throw new Error(event.error ?? 'Streaming error');
        }
      }
    }
  } finally {
    reader.releaseLock();
  }

  if (!finalMessage) {
    throw new Error('Stream ended without a final message');
  }

  return { message: finalMessage, sessionId: finalSessionId };
}

/** Response shape for the chat history endpoint. */
export interface ChatHistoryResponse {
  sessionId: string;
  messages: ChatMessage[];
}

/** Fetch conversation history for a session. */
export async function fetchChatHistory(sessionId: string): Promise<ChatHistoryResponse> {
  const headers = await buildAuthHeaders();
  const response = await fetch(`/api/chat/history?sessionId=${encodeURIComponent(sessionId)}`, {
    method: 'GET',
    headers,
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch history: ${response.status}`);
  }
  return response.json() as Promise<ChatHistoryResponse>;
}

/** Clear conversation history for a session. */
export async function clearChatHistory(sessionId: string): Promise<void> {
  const headers = await buildAuthHeaders();
  const response = await fetch(`/api/chat/history?sessionId=${encodeURIComponent(sessionId)}`, {
    method: 'DELETE',
    headers,
  });
  if (!response.ok && response.status !== 204) {
    throw new Error(`Failed to clear history: ${response.status}`);
  }
}
