import Container from '@mui/material/Container';
import Box from '@mui/material/Box';
import Skeleton from '@mui/material/Skeleton';

export default function SearchLoading() {
  return (
    <Container maxWidth="xl" sx={{ py: 2 }}>
      <Box sx={{ mb: 3 }}>
        <Skeleton variant="text" width={120} height={48} />
        <Skeleton variant="text" width={280} height={24} />
      </Box>
      <Box sx={{ display: 'flex', gap: 3 }}>
        <Box sx={{ width: 280, flexShrink: 0 }}>
          <Skeleton variant="rounded" height={300} />
        </Box>
        <Box sx={{ flex: 1 }}>
          {Array.from({ length: 5 }, (_, i) => (
            <Skeleton key={i} variant="rounded" height={140} sx={{ mb: 2 }} />
          ))}
        </Box>
      </Box>
    </Container>
  );
}
