'use client';

/**
 * ChatInput — multi-line text input for sending chat messages.
 *
 * - Auto-expands up to 4 lines
 * - Sends on Enter (Shift+Enter for new line)
 * - Send button with loading state
 * - Disabled while streaming
 * - Character count indicator near the 4000-char limit
 */

import { useRef, useState } from 'react';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import IconButton from '@mui/material/IconButton';
import Typography from '@mui/material/Typography';
import SendIcon from '@mui/icons-material/Send';
import CircularProgress from '@mui/material/CircularProgress';

const MAX_CHARS = 4000;
const CHAR_COUNT_THRESHOLD = 3500;

export interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export default function ChatInput({
  onSend,
  disabled = false,
  placeholder = 'Ask about APIs…',
}: ChatInputProps) {
  const [value, setValue] = useState('');
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const canSend = value.trim().length > 0 && !disabled && value.length <= MAX_CHARS;

  const handleSend = () => {
    if (!canSend) return;
    const text = value.trim();
    setValue('');
    onSend(text);
    // Return focus to the input
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const charCount = value.length;
  const showCount = charCount >= CHAR_COUNT_THRESHOLD;
  const isOverLimit = charCount > MAX_CHARS;

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'flex-end',
        gap: 1,
        p: 1,
        borderTop: 1,
        borderColor: 'divider',
        bgcolor: 'background.paper',
      }}
    >
      <Box sx={{ flex: 1, position: 'relative' }}>
        <TextField
          inputRef={inputRef}
          fullWidth
          multiline
          maxRows={4}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          error={isOverLimit}
          size="small"
          slotProps={{
            htmlInput: {
              'aria-label': 'Chat message input',
              'data-testid': 'chat-input',
              maxLength: MAX_CHARS + 100,
            },
          }}
          sx={{ '& .MuiOutlinedInput-root': { borderRadius: 3 } }}
        />
        {showCount && (
          <Typography
            variant="caption"
            sx={{
              position: 'absolute',
              bottom: 6,
              right: 12,
              color: isOverLimit ? 'error.main' : 'text.disabled',
              pointerEvents: 'none',
            }}
          >
            {charCount}/{MAX_CHARS}
          </Typography>
        )}
      </Box>

      <IconButton
        color="primary"
        onClick={handleSend}
        disabled={!canSend}
        aria-label="Send message"
        data-testid="send-button"
        sx={{
          mb: 0.25,
          bgcolor: canSend ? 'primary.main' : undefined,
          color: canSend ? 'primary.contrastText' : undefined,
          '&:hover': { bgcolor: canSend ? 'primary.dark' : undefined },
          '&.Mui-disabled': { bgcolor: 'action.disabledBackground' },
        }}
      >
        {disabled ? <CircularProgress size={20} color="inherit" /> : <SendIcon fontSize="small" />}
      </IconButton>
    </Box>
  );
}
