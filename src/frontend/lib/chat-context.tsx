'use client';

/**
 * Chat context provider.
 *
 * Manages chat session state (messages, streaming, session ID) and exposes
 * actions (sendMessage, newConversation) via React context.
 *
 * Wrap your application (or the root layout) with <ChatProvider> so that
 * any component tree can access the shared chat state.
 */

import React, { createContext, useCallback, useContext, useRef, useState } from 'react';
import type { ChatMessage } from '@apic-vibe-portal/shared';
import { streamChatMessage } from '@/lib/chat-api';
import { useAnalytics } from '@/lib/analytics/use-analytics';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ChatContextValue {
  /** Current session ID (null until first message is sent). */
  sessionId: string | null;
  /** All messages in the current conversation. */
  messages: ChatMessage[];
  /** True while a streaming response is in progress. */
  isStreaming: boolean;
  /** Error message from the last failed request, or null. */
  error: string | null;
  /** Whether the embedded chat side panel is open. */
  isPanelOpen: boolean;
  /** Send a user message and stream the assistant response. */
  sendMessage: (text: string) => Promise<void>;
  /** Reset the conversation (new session). */
  newConversation: () => void;
  /** Open or close the embedded side panel. */
  setPanelOpen: (open: boolean) => void;
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const ChatContext = createContext<ChatContextValue | null>(null);

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const { track } = useAnalytics();

  // AbortController for cancelling in-flight requests
  const abortRef = useRef<AbortController | null>(null);
  const messageCountRef = useRef(0);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isStreaming) return;

      setError(null);

      // Add the user message immediately
      const userMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content: text.trim(),
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setIsStreaming(true);

      // Create a placeholder for the streaming assistant response
      const assistantId = crypto.randomUUID();
      const assistantPlaceholder: ChatMessage = {
        id: assistantId,
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantPlaceholder]);

      // Abort any previous in-flight request
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const { message: finalMessage, sessionId: newSessionId } = await streamChatMessage({
          message: text.trim(),
          sessionId,
          signal: controller.signal,
          onStart: (sid) => {
            setSessionId(sid);
          },
          onToken: (token) => {
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantId ? { ...m, content: m.content + token } : m))
            );
          },
        });

        // Replace placeholder with the authoritative final message
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...finalMessage, id: assistantId } : m))
        );
        setSessionId(newSessionId);

        messageCountRef.current += 2; // user + assistant
        track.chatInteraction({
          chatSessionId: newSessionId,
          messageCount: messageCountRef.current,
          agentUsed: 'default',
        });
      } catch (err) {
        if ((err as Error).name === 'AbortError') {
          // Remove the placeholder on abort
          setMessages((prev) => prev.filter((m) => m.id !== assistantId));
        } else {
          const msg = err instanceof Error ? err.message : 'Failed to get response';
          setError(msg);
          // Replace placeholder with error message
          setMessages((prev) =>
            prev.map((m) => (m.id === assistantId ? { ...m, content: '⚠️ ' + msg } : m))
          );
        }
      } finally {
        setIsStreaming(false);
      }
    },
    [isStreaming, sessionId, track]
  );

  const newConversation = useCallback(() => {
    abortRef.current?.abort();
    setMessages([]);
    setSessionId(null);
    setError(null);
    setIsStreaming(false);
    messageCountRef.current = 0;
  }, []);

  const setPanelOpen = useCallback((open: boolean) => {
    setIsPanelOpen(open);
  }, []);

  return (
    <ChatContext.Provider
      value={{
        sessionId,
        messages,
        isStreaming,
        error,
        isPanelOpen,
        sendMessage,
        newConversation,
        setPanelOpen,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useChatContext(): ChatContextValue {
  const ctx = useContext(ChatContext);
  if (!ctx) {
    throw new Error('useChatContext must be used within a ChatProvider');
  }
  return ctx;
}
