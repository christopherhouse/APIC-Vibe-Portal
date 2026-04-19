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

  // Auto-scroll to the latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
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
