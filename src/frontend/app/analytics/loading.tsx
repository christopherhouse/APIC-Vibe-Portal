import { Box, CircularProgress, Container } from '@mui/material';

export default function AnalyticsLoading() {
  return (
    <Container maxWidth="xl" sx={{ mt: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    </Container>
  );
}
