/**
 * Agent test dialog component.
 */

import { useState } from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Box from '@mui/material/Box';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import Typography from '@mui/material/Typography';
import Divider from '@mui/material/Divider';

import { testAgent, type AgentTestRequest } from '@/lib/admin-agent-api';

interface AgentTestDialogProps {
  open: boolean;
  agentId: string;
  onClose: () => void;
  onSuccess: (message: string) => void;
}

export default function AgentTestDialog({ open, agentId, onClose, onSuccess }: AgentTestDialogProps) {
  const [query, setQuery] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<{ success: boolean; response: string; responseTimeMs: number; error?: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!query.trim()) {
      setError('Please enter a query');
      return;
    }

    setIsSubmitting(true);
    setError(null);
    setResult(null);

    try {
      const request: AgentTestRequest = {
        query: query.trim(),
      };

      const response = await testAgent(agentId, request);
      setResult({
        success: response.success,
        response: response.response,
        responseTimeMs: response.responseTimeMs,
        error: response.error,
      });

      if (response.success) {
        onSuccess(`Test completed successfully in ${response.responseTimeMs.toFixed(0)}ms`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to test agent');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setQuery('');
    setResult(null);
    setError(null);
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>Test Agent</DialogTitle>
      <DialogContent>
        <Box sx={{ pt: 2 }}>
          <TextField
            fullWidth
            multiline
            rows={4}
            label="Test Query"
            placeholder="Enter a sample query to test the agent..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={isSubmitting}
            data-testid="test-query-input"
          />

          {error && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {error}
            </Alert>
          )}

          {result && (
            <Box sx={{ mt: 2 }}>
              <Divider sx={{ mb: 2 }} />
              <Typography variant="subtitle2" gutterBottom>
                Response ({result.responseTimeMs.toFixed(0)}ms)
              </Typography>
              {result.success ? (
                <Alert severity="success" sx={{ mt: 1 }}>
                  <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap' }}>
                    {result.response}
                  </Typography>
                </Alert>
              ) : (
                <Alert severity="error" sx={{ mt: 1 }}>
                  <Typography variant="body2">
                    {result.error || 'Test failed'}
                  </Typography>
                </Alert>
              )}
            </Box>
          )}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={isSubmitting}>
          Close
        </Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={isSubmitting || !query.trim()}
          data-testid="test-submit-button"
        >
          {isSubmitting ? <CircularProgress size={24} /> : 'Test Agent'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
