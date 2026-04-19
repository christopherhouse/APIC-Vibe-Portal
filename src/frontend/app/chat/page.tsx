'use client';

/**
 * /chat — Full-page AI chat interface.
 *
 * Centered, max-width layout with the ChatContainer taking the full
 * available viewport height below the header.
 */

import Container from '@mui/material/Container';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import AddIcon from '@mui/icons-material/Add';
import { useChatContext } from '@/lib/chat-context';
import ChatContainer from './components/ChatContainer';

export default function ChatPage() {
  const { newConversation, messages } = useChatContext();

  return (
    <Container
      maxWidth="md"
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: `calc(100vh - var(--header-height) - var(--footer-height, 0px) - 48px)`,
        py: 2,
      }}
    >
      {/* Page header */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          mb: 2,
          pb: 1,
          borderBottom: 1,
          borderColor: 'divider',
        }}
      >
        <Typography variant="h5" component="h1" sx={{ flex: 1, fontWeight: 600 }}>
          AI Assistant
        </Typography>
        {messages.length > 0 && (
          <Tooltip title="New conversation">
            <IconButton
              onClick={newConversation}
              aria-label="New conversation"
              data-testid="new-conversation-button"
            >
              <AddIcon />
            </IconButton>
          </Tooltip>
        )}
      </Box>

      {/* Main chat area */}
      <Box sx={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <ChatContainer />
      </Box>
    </Container>
  );
}
