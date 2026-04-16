import Box from '@mui/material/Box';
import Skeleton from '@mui/material/Skeleton';
import Container from '@mui/material/Container';

/** Loading skeleton shown while the catalog page is streaming. */
export default function CatalogLoading() {
  return (
    <Container maxWidth="xl" sx={{ py: 2 }}>
      {/* Title skeleton */}
      <Skeleton variant="text" width={240} height={48} sx={{ mb: 1 }} />
      <Skeleton variant="text" width={360} height={24} sx={{ mb: 3 }} />

      {/* Toolbar skeleton */}
      <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
        <Skeleton variant="rounded" width={200} height={40} />
        <Box sx={{ flex: 1 }} />
        <Skeleton variant="rounded" width={80} height={40} />
      </Box>

      {/* Grid skeleton */}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: '1fr 1fr 1fr' },
          gap: 3,
        }}
      >
        {Array.from({ length: 6 }, (_, i) => (
          <Skeleton key={i} variant="rounded" height={200} />
        ))}
      </Box>
    </Container>
  );
}
