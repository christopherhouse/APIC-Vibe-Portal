'use client';

/**
 * ChatSidePanel — collapsible chat panel accessible from every page.
 *
 * A floating action button (bottom-right) toggles the panel.
 * The panel slides in from the right side and contains the full
 * ChatContainer so the conversation persists across navigation.
 * On mobile the panel becomes a full-screen overlay.
 */

import Box from '@mui/material/Box';
import Drawer from '@mui/material/Drawer';
import Fab from '@mui/material/Fab';
import IconButton from '@mui/material/IconButton';
import Typography from '@mui/material/Typography';
import Divider from '@mui/material/Divider';
import Tooltip from '@mui/material/Tooltip';
import ChatIcon from '@mui/icons-material/Chat';
import CloseIcon from '@mui/icons-material/Close';
import AddIcon from '@mui/icons-material/Add';
import useMediaQuery from '@mui/material/useMediaQuery';
import { useTheme } from '@mui/material/styles';
import { useChatContext } from '@/lib/chat-context';
import ChatContainer from './ChatContainer';

const PANEL_WIDTH = 380;

export default function ChatSidePanel() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const { isPanelOpen, setPanelOpen, newConversation, messages } = useChatContext();

  const togglePanel = () => setPanelOpen(!isPanelOpen);
  const closePanel = () => setPanelOpen(false);

  const handleNewConversation = () => {
    newConversation();
  };

  return (
    <>
      {/* Floating action button to open the panel */}
      <Tooltip title={isPanelOpen ? 'Close AI Assistant' : 'Open AI Assistant'} placement="left">
        <Fab
          color="primary"
          size="medium"
          onClick={togglePanel}
          aria-label={isPanelOpen ? 'Close AI Assistant' : 'Open AI Assistant'}
          data-testid="chat-fab"
          sx={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            zIndex: (t) => t.zIndex.drawer + 2,
          }}
        >
          {isPanelOpen ? <CloseIcon /> : <ChatIcon />}
        </Fab>
      </Tooltip>

      {/* Slide-in panel */}
      <Drawer
        anchor="right"
        open={isPanelOpen}
        onClose={closePanel}
        variant={isMobile ? 'temporary' : 'persistent'}
        data-testid="chat-side-panel"
        slotProps={{
          paper: {
            sx: {
              width: isMobile ? '100vw' : PANEL_WIDTH,
              display: 'flex',
              flexDirection: 'column',
              // Push panel below the app header
              top: isMobile ? 0 : 'var(--header-height)',
              height: isMobile ? '100%' : `calc(100% - var(--header-height))`,
              zIndex: (t) => t.zIndex.drawer + 1,
            },
          },
        }}
      >
        {/* Panel header */}
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            px: 2,
            py: 1,
            borderBottom: 1,
            borderColor: 'divider',
          }}
        >
          <ChatIcon sx={{ mr: 1, color: 'primary.main', fontSize: 20 }} />
          <Typography variant="subtitle1" sx={{ fontWeight: 600, flex: 1 }}>
            AI Assistant
          </Typography>
          {messages.length > 0 && (
            <Tooltip title="New conversation">
              <IconButton
                size="small"
                onClick={handleNewConversation}
                aria-label="New conversation"
                data-testid="new-conversation-button"
              >
                <AddIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          )}
          {isMobile && (
            <IconButton size="small" onClick={closePanel} aria-label="Close panel">
              <CloseIcon fontSize="small" />
            </IconButton>
          )}
        </Box>
        <Divider />

        {/* Chat content */}
        <Box sx={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <ChatContainer compact />
        </Box>
      </Drawer>
    </>
  );
}
