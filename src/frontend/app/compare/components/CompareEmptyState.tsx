'use client';

import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import CompareArrowsIcon from '@mui/icons-material/CompareArrows';
import { useRouter } from 'next/navigation';

export default function CompareEmptyState() {
  const router = useRouter();

  return (
    <Box
      data-testid="compare-empty-state"
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: 400,
        gap: 3,
        textAlign: 'center',
        p: 4,
      }}
    >
      <CompareArrowsIcon sx={{ fontSize: 64, color: 'text.disabled' }} />
      <Box>
        <Typography variant="h5" gutterBottom>
          No APIs selected for comparison
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 480, mx: 'auto' }}>
          Select 2 to 5 APIs to compare them side by side. Use the search below or browse the
          catalog to add APIs.
        </Typography>
      </Box>
      <Button variant="contained" onClick={() => router.push('/catalog')}>
        Browse Catalog
      </Button>
    </Box>
  );
}
