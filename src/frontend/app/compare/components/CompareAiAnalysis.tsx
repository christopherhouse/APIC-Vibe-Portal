'use client';

import { useState } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Paper from '@mui/material/Paper';
import Alert from '@mui/material/Alert';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import ReactMarkdown from 'react-markdown';
import type { CompareResponse } from '@/lib/compare-api';
import { compareApisWithAi } from '@/lib/compare-api';

export interface CompareAiAnalysisProps {
  /** Current comparison result (may already include aiAnalysis). */
  result: CompareResponse;
  onAnalysisLoaded: (updated: CompareResponse) => void;
}

export default function CompareAiAnalysis({ result, onAnalysisLoaded }: CompareAiAnalysisProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRequestAnalysis = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const apiIds = result.apis.map((a) => a.name);
      const updated = await compareApisWithAi({ apiIds });
      onAnalysisLoaded(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate AI analysis');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Box data-testid="compare-ai-analysis">
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <AutoAwesomeIcon color="primary" />
        <Typography variant="h6">AI Analysis</Typography>
      </Box>

      {result.aiAnalysis ? (
        <Paper variant="outlined" sx={{ p: 3 }}>
          <Typography component="div" variant="body1">
            <ReactMarkdown>{result.aiAnalysis}</ReactMarkdown>
          </Typography>
        </Paper>
      ) : (
        <Box>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}
          <Button
            variant="outlined"
            startIcon={isLoading ? <CircularProgress size={16} /> : <AutoAwesomeIcon />}
            onClick={() => void handleRequestAnalysis()}
            disabled={isLoading}
            data-testid="request-ai-analysis-button"
          >
            {isLoading ? 'Generating analysis…' : 'Generate AI Analysis'}
          </Button>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
            Uses AI to provide narrative comparison, use-case recommendations, and trade-offs.
          </Typography>
        </Box>
      )}
    </Box>
  );
}
