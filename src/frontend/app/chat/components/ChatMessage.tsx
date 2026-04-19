'use client';

/**
 * ChatMessage — renders a single chat message bubble.
 *
 * - User messages: right-aligned colored bubble
 * - Assistant messages: left-aligned, markdown rendered, with optional citations
 * - Shows timestamp and a copy-to-clipboard button on assistant messages
 */

import { useState } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import CheckIcon from '@mui/icons-material/Check';
import { useTheme } from '@mui/material/styles';
import ReactMarkdown from 'react-markdown';
import type { ChatMessage as ChatMessageType } from '@apic-vibe-portal/shared';
import ChatCitations from './ChatCitations';
import { formatDate } from '@/lib/utils';

export interface ChatMessageProps {
  message: ChatMessageType;
}

export default function ChatMessageBubble({ message }: ChatMessageProps) {
  const theme = useTheme();
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API may be unavailable
    }
  };

  return (
    <Box
      data-testid={`chat-message-${message.id}`}
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: isUser ? 'flex-end' : 'flex-start',
        mb: 1.5,
        px: 1,
      }}
    >
      <Box
        sx={{
          maxWidth: { xs: '90%', sm: '75%' },
          bgcolor: isUser
            ? theme.palette.primary.main
            : theme.palette.mode === 'dark'
              ? theme.palette.grey[800]
              : theme.palette.grey[100],
          color: isUser ? theme.palette.primary.contrastText : 'text.primary',
          borderRadius: isUser ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
          px: 2,
          py: 1.5,
          position: 'relative',
        }}
      >
        {isUser ? (
          <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
            {message.content}
          </Typography>
        ) : (
          <Box
            sx={{
              '& p': { m: 0, mb: 1, '&:last-child': { mb: 0 } },
              '& ul, & ol': { mt: 0, mb: 1, pl: 2.5 },
              '& li': { mb: 0.5 },
              '& code': {
                fontFamily: 'monospace',
                fontSize: '0.85em',
                bgcolor: 'action.hover',
                px: 0.5,
                py: 0.25,
                borderRadius: 0.5,
              },
              '& pre': {
                bgcolor: 'action.hover',
                borderRadius: 1,
                p: 1.5,
                overflow: 'auto',
                mb: 1,
                '& code': { bgcolor: 'transparent', p: 0 },
              },
              '& strong': { fontWeight: 700 },
              '& em': { fontStyle: 'italic' },
              '& blockquote': {
                borderLeft: '3px solid',
                borderColor: 'divider',
                pl: 1.5,
                ml: 0,
                color: 'text.secondary',
              },
            }}
          >
            <ReactMarkdown>{message.content || '\u00A0'}</ReactMarkdown>
          </Box>
        )}
      </Box>

      {/* Citations below assistant bubble */}
      {!isUser && message.citations && message.citations.length > 0 && (
        <Box sx={{ maxWidth: { xs: '90%', sm: '75%' }, mt: 0.5 }}>
          <ChatCitations citations={message.citations} />
        </Box>
      )}

      {/* Timestamp row with copy button for assistant messages */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 0.5,
          mt: 0.25,
          flexDirection: isUser ? 'row-reverse' : 'row',
        }}
      >
        <Typography variant="caption" color="text.disabled" sx={{ px: 0.5 }}>
          {formatDate(message.timestamp)}
        </Typography>
        {!isUser && (
          <Tooltip title={copied ? 'Copied!' : 'Copy message'}>
            <IconButton
              size="small"
              onClick={handleCopy}
              aria-label="copy message"
              data-testid="copy-button"
              sx={{ p: 0.25 }}
            >
              {copied ? (
                <CheckIcon sx={{ fontSize: 14, color: 'success.main' }} />
              ) : (
                <ContentCopyIcon sx={{ fontSize: 14 }} />
              )}
            </IconButton>
          </Tooltip>
        )}
      </Box>
    </Box>
  );
}
