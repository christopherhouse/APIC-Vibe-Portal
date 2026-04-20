'use client';

/**
 * Admin — Agent Management page.
 *
 * Only accessible to users with the `Portal.Admin` role.
 *
 * Allows admins to:
 * - View all registered agents
 * - View agent details and configuration
 * - View agent usage statistics
 * - Test agents with sample queries
 */

import { useCallback, useEffect, useState } from 'react';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Alert from '@mui/material/Alert';
import Snackbar from '@mui/material/Snackbar';
import Stack from '@mui/material/Stack';
import BlockIcon from '@mui/icons-material/Block';
import Grid from '@mui/material/Grid';

import { useAuth } from '@/lib/auth/use-auth';
import { fetchAgents, type AgentInfo } from '@/lib/admin-agent-api';

import AgentCard from './components/AgentCard';
import AgentDetailsDialog from './components/AgentDetailsDialog';
import AgentTestDialog from './components/AgentTestDialog';

const ADMIN_ROLE = 'Portal.Admin';

export default function AgentsPage() {
  const { user, isAuthenticated } = useAuth();
  const isAdmin = Boolean(user?.roles.includes(ADMIN_ROLE));

  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Details dialog state
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);

  // Test dialog state
  const [testDialogOpen, setTestDialogOpen] = useState(false);
  const [testAgentId, setTestAgentId] = useState<string | null>(null);

  // Success / error toast
  const [snackbar, setSnackbar] = useState<{
    message: string;
    severity: 'success' | 'error';
  } | null>(null);

  // ---------------------------------------------------------------------------
  // Data loading
  // ---------------------------------------------------------------------------

  const loadAgents = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const data = await fetchAgents();
      setAgents(data);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to load agents.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated && isAdmin) {
      void loadAgents();
    } else {
      setIsLoading(false);
    }
  }, [isAuthenticated, isAdmin, loadAgents]);

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  const handleViewDetails = (agentId: string) => {
    setSelectedAgentId(agentId);
    setDetailsDialogOpen(true);
  };

  const handleTestAgent = (agentId: string) => {
    setTestAgentId(agentId);
    setTestDialogOpen(true);
  };

  // ---------------------------------------------------------------------------
  // Access guard
  // ---------------------------------------------------------------------------

  if (!isAdmin && !isLoading) {
    return (
      <Container maxWidth="sm" sx={{ py: 8, textAlign: 'center' }}>
        <BlockIcon sx={{ fontSize: 64, color: 'error.main', mb: 2 }} />
        <Typography variant="h5" gutterBottom>
          Access Denied
        </Typography>
        <Typography variant="body1" color="text.secondary">
          You need the <strong>Portal.Admin</strong> role to manage agents.
        </Typography>
      </Container>
    );
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <Container maxWidth="xl" sx={{ py: 2 }}>
      {/* Page header */}
      <Stack direction="column" spacing={2} sx={{ mb: 3 }}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            Agent Management
          </Typography>
          <Typography variant="body1" color="text.secondary">
            View and manage AI agents registered in the portal. Monitor agent status, view usage
            statistics, and test agent capabilities.
          </Typography>
        </Box>
      </Stack>

      {/* Load error */}
      {loadError && (
        <Alert severity="error" sx={{ mb: 2 }} data-testid="load-error">
          {loadError}
        </Alert>
      )}

      {/* Agents grid */}
      <Grid container spacing={3}>
        {agents.map((agent) => (
          <Grid item xs={12} md={6} lg={4} key={agent.agentId}>
            <AgentCard
              agent={agent}
              onViewDetails={handleViewDetails}
              onTest={handleTestAgent}
            />
          </Grid>
        ))}
      </Grid>

      {isLoading && agents.length === 0 && (
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <Typography variant="body1" color="text.secondary">
            Loading agents...
          </Typography>
        </Box>
      )}

      {!isLoading && agents.length === 0 && (
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <Typography variant="body1" color="text.secondary">
            No agents registered.
          </Typography>
        </Box>
      )}

      {/* Agent details dialog */}
      {selectedAgentId && (
        <AgentDetailsDialog
          open={detailsDialogOpen}
          agentId={selectedAgentId}
          onClose={() => setDetailsDialogOpen(false)}
        />
      )}

      {/* Agent test dialog */}
      {testAgentId && (
        <AgentTestDialog
          open={testDialogOpen}
          agentId={testAgentId}
          onClose={() => setTestDialogOpen(false)}
          onSuccess={(message) => setSnackbar({ message, severity: 'success' })}
        />
      )}

      {/* Success / error toast */}
      <Snackbar
        open={Boolean(snackbar)}
        autoHideDuration={4000}
        onClose={() => setSnackbar(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        {snackbar ? (
          <Alert
            onClose={() => setSnackbar(null)}
            severity={snackbar.severity}
            variant="filled"
            data-testid="snackbar-alert"
          >
            {snackbar.message}
          </Alert>
        ) : (
          <span />
        )}
      </Snackbar>
    </Container>
  );
}
