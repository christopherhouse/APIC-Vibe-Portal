/**
 * Agent details dialog component.
 */

import { useEffect, useState } from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import Stack from '@mui/material/Stack';
import Divider from '@mui/material/Divider';

import {
  fetchAgentDetail,
  fetchAgentStats,
  type AgentDetail,
  type AgentStats,
} from '@/lib/admin-agent-api';

interface AgentDetailsDialogProps {
  open: boolean;
  agentId: string;
  onClose: () => void;
}

export default function AgentDetailsDialog({ open, agentId, onClose }: AgentDetailsDialogProps) {
  const [detail, setDetail] = useState<AgentDetail | null>(null);
  const [stats, setStats] = useState<AgentStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;

    const loadData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const [detailData, statsData] = await Promise.all([
          fetchAgentDetail(agentId),
          fetchAgentStats(agentId),
        ]);
        setDetail(detailData);
        setStats(statsData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load agent details');
      } finally {
        setIsLoading(false);
      }
    };

    void loadData();
  }, [open, agentId]);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Agent Details</DialogTitle>
      <DialogContent>
        {isLoading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        )}

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {detail && (
          <Box>
            {/* Basic info */}
            <Stack spacing={2}>
              <Box>
                <Typography variant="h6" gutterBottom>
                  {detail.name}
                </Typography>
                <Typography variant="body2" color="text.secondary" paragraph>
                  {detail.description}
                </Typography>
                <Chip
                  label={detail.status}
                  color={detail.status === 'active' ? 'success' : 'default'}
                  size="small"
                />
              </Box>

              <Divider />

              {/* Capabilities */}
              <Box>
                <Typography variant="subtitle1" gutterBottom>
                  Capabilities
                </Typography>
                <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                  {detail.capabilities.map((cap) => (
                    <Chip key={cap} label={cap} size="small" variant="outlined" />
                  ))}
                </Stack>
              </Box>

              {/* Statistics */}
              {stats && (
                <>
                  <Divider />
                  <Box>
                    <Typography variant="subtitle1" gutterBottom>
                      Usage Statistics
                    </Typography>
                    <Stack spacing={1}>
                      <Typography variant="body2">
                        <strong>Queries Handled:</strong> {stats.queriesHandled}
                      </Typography>
                      <Typography variant="body2">
                        <strong>Avg Response Time:</strong> {stats.avgResponseTimeMs.toFixed(2)} ms
                      </Typography>
                      <Typography variant="body2">
                        <strong>Success Rate:</strong> {stats.successRate.toFixed(1)}%
                      </Typography>
                      {stats.lastUsedAt && (
                        <Typography variant="body2">
                          <strong>Last Used:</strong> {new Date(stats.lastUsedAt).toLocaleString()}
                        </Typography>
                      )}
                    </Stack>
                  </Box>
                </>
              )}

              {/* Configuration */}
              <Divider />
              <Box>
                <Typography variant="subtitle1" gutterBottom>
                  Configuration
                </Typography>
                <Typography
                  variant="body2"
                  component="pre"
                  sx={{ whiteSpace: 'pre-wrap', fontSize: '0.875rem' }}
                >
                  {JSON.stringify(detail.configuration, null, 2)}
                </Typography>
              </Box>
            </Stack>
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}
