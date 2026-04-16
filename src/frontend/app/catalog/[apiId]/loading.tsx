import Box from '@mui/material/Box';
import Skeleton from '@mui/material/Skeleton';
import Container from '@mui/material/Container';

/** Loading skeleton for the API detail page. */
export default function ApiDetailLoading() {
  return (
    <Container maxWidth="lg" sx={{ py: 2 }}>
      {/* Breadcrumb skeleton */}
      <Skeleton variant="text" width={200} height={24} sx={{ mb: 1 }} />

      {/* Title skeleton */}
      <Skeleton variant="text" width={300} height={48} sx={{ mb: 1 }} />

      {/* Badges skeleton */}
      <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
        <Skeleton variant="rounded" width={60} height={24} />
        <Skeleton variant="rounded" width={80} height={24} />
      </Box>

      {/* Description skeleton */}
      <Skeleton variant="text" width="60%" height={24} sx={{ mb: 1 }} />
      <Skeleton variant="text" width={200} height={16} sx={{ mb: 3 }} />

      {/* Tabs skeleton */}
      <Skeleton variant="rounded" width="100%" height={48} sx={{ mb: 3 }} />

      {/* Content skeleton */}
      <Skeleton variant="rounded" width="100%" height={300} />
    </Container>
  );
}
