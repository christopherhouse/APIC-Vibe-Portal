'use client';

import { useEffect } from 'react';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';
import Alert from '@mui/material/Alert';

export default function CatalogError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('Catalog error:', error);
  }, [error]);

  return (
    <Container maxWidth="sm">
      <Box sx={{ py: 8, textAlign: 'center' }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Failed to load API catalog
        </Typography>
        <Alert severity="error" sx={{ mb: 3, textAlign: 'left' }}>
          {error.message || 'An unexpected error occurred while loading the catalog.'}
        </Alert>
        <Button variant="contained" onClick={reset}>
          Try again
        </Button>
      </Box>
    </Container>
  );
}
