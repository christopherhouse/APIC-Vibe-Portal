'use client';

import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Skeleton from '@mui/material/Skeleton';
import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';

export interface ApiSpecViewerProps {
  specContent: string | null;
  isLoading?: boolean;
  error?: string | null;
  onRetry?: () => void;
}

/**
 * Renders an OpenAPI specification document.
 * Displays the raw spec content in a formatted code block.
 * A full Swagger UI renderer can be added later.
 */
export default function ApiSpecViewer({
  specContent,
  isLoading,
  error,
  onRetry,
}: ApiSpecViewerProps) {
  if (isLoading) {
    return (
      <Box data-testid="spec-viewer-skeleton">
        <Skeleton variant="rounded" height={400} />
      </Box>
    );
  }

  if (error) {
    return (
      <Box data-testid="spec-viewer-error">
        <Alert
          severity="error"
          sx={{ mb: 2 }}
          action={
            onRetry && (
              <Button color="inherit" size="small" onClick={onRetry}>
                Retry
              </Button>
            )
          }
        >
          {error}
        </Alert>
      </Box>
    );
  }

  if (!specContent) {
    return (
      <Box data-testid="spec-viewer-empty">
        <Typography variant="body1" color="text.secondary">
          No specification available. Select a version to view its API specification.
        </Typography>
      </Box>
    );
  }

  // Try to parse and pretty-print JSON specs
  let displayContent = specContent;
  try {
    const parsed = JSON.parse(specContent);
    displayContent = JSON.stringify(parsed, null, 2);
  } catch {
    // Not JSON, display as-is (could be YAML)
  }

  return (
    <Box data-testid="spec-viewer">
      <Paper
        variant="outlined"
        sx={{
          p: 2,
          maxHeight: 600,
          overflow: 'auto',
          bgcolor: 'grey.50',
        }}
      >
        <Box
          component="pre"
          sx={{
            m: 0,
            fontFamily: 'monospace',
            fontSize: '0.85rem',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
          }}
        >
          {displayContent}
        </Box>
      </Paper>
    </Box>
  );
}
