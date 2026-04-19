'use client';

/**
 * ChatContainer — the main chat UI shell.
 *
 * Renders the message list, typing indicator, input area, and (when
 * the conversation is empty) the suggested starter prompts.
 * Accepts a `compact` prop so it can be reused inside the side panel.
 */

import Box from '@mui/material/Box';
import Alert from '@mui/material/Alert';
import { useChatContext } from '@/lib/chat-context';
import ChatMessageList from './ChatMessageList';
import ChatInput from './ChatInput';
import ChatSuggestions from './ChatSuggestions';

export interface ChatContainerProps {
  /** When true, reduces padding for use inside the collapsible side panel. */
  compact?: boolean;
}

export default function ChatContainer({ compact = false }: ChatContainerProps) {
  const { messages, isStreaming, error, sendMessage } = useChatContext();

  const isEmpty = messages.length === 0;

  return (
    <Box
      data-testid="chat-container"
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        overflow: 'hidden',
      }}
    >
      {error && (
        <Alert severity="error" sx={{ mx: compact ? 1 : 2, mt: 1, borderRadius: 2 }}>
          {error}
        </Alert>
      )}

      {isEmpty ? (
        <Box sx={{ flex: 1, overflowY: 'auto' }}>
          <ChatSuggestions onSelect={sendMessage} />
        </Box>
      ) : (
        <ChatMessageList messages={messages} isStreaming={isStreaming} />
      )}

      <ChatInput
        onSend={sendMessage}
        disabled={isStreaming}
        placeholder={compact ? 'Ask about APIs…' : 'Ask me anything about APIs…'}
      />
    </Box>
  );
}
