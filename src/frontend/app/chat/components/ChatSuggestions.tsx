'use client';

/**
 * ChatSuggestions — starter prompt buttons shown when the conversation is empty.
 */

import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';

const STARTER_PROMPTS = [
  'What APIs are available for payment processing?',
  'Show me APIs in production',
  'Which APIs support GraphQL?',
  'Help me find an API for user authentication',
];

export interface ChatSuggestionsProps {
  onSelect: (prompt: string) => void;
}

export default function ChatSuggestions({ onSelect }: ChatSuggestionsProps) {
  return (
    <Box
      data-testid="chat-suggestions"
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 2,
        py: 4,
        px: 2,
      }}
    >
      <AutoAwesomeIcon sx={{ fontSize: 48, color: 'primary.main', opacity: 0.8 }} />
      <Typography variant="h6" color="text.secondary" sx={{ textAlign: 'center' }}>
        How can I help you discover APIs?
      </Typography>
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' },
          gap: 1,
          width: '100%',
          maxWidth: 600,
        }}
      >
        {STARTER_PROMPTS.map((prompt) => (
          <Button
            key={prompt}
            variant="outlined"
            size="small"
            onClick={() => onSelect(prompt)}
            data-testid="suggestion-prompt"
            sx={{
              textAlign: 'left',
              justifyContent: 'flex-start',
              textTransform: 'none',
              py: 1.5,
              px: 2,
              borderRadius: 2,
              whiteSpace: 'normal',
              lineHeight: 1.4,
            }}
          >
            {prompt}
          </Button>
        ))}
      </Box>
    </Box>
  );
}
