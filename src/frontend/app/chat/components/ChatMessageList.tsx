'use client';

/**
 * ChatMessageList — scrollable list of chat messages.
 *
 * Automatically scrolls to the bottom whenever messages change.
 * Renders the typing indicator when the AI is streaming.
 */

import { useEffect, useRef } from 'react';
import Box from '@mui/material/Box';
import type { ChatMessage } from '@apic-vibe-portal/shared';
import ChatMessageBubble from './ChatMessage';
import ChatTypingIndicator from './ChatTypingIndicator';

export interface ChatMessageListProps {
  messages: ChatMessage[];
  isStreaming: boolean;
}

export default function ChatMessageList({ messages, isStreaming }: ChatMessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const previousMessageCountRef = useRef(messages.length);

  // Scroll to the bottom on new messages.
  // During streaming (frequent token updates to the last message) use 'auto' to avoid
  // repeated smooth-scroll animations that cause jank.
  // On a discrete new message addition, use 'smooth' for a polished feel.
  useEffect(() => {
    const hasNewMessage = messages.length > previousMessageCountRef.current;
    const behavior: ScrollBehavior = !isStreaming && hasNewMessage ? 'smooth' : 'auto';
    bottomRef.current?.scrollIntoView({ behavior });
    previousMessageCountRef.current = messages.length;
  }, [messages, isStreaming]);

  return (
    <Box
      data-testid="chat-message-list"
      sx={{
        flex: 1,
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        py: 1,
      }}
    >
      {messages.map((msg) => (
        <ChatMessageBubble key={msg.id} message={msg} />
      ))}

      {/* Typing indicator shown before the first token arrives */}
      {isStreaming && messages.at(-1)?.role === 'assistant' && messages.at(-1)?.content === '' && (
        <ChatTypingIndicator />
      )}

      <div ref={bottomRef} />
    </Box>
  );
}
