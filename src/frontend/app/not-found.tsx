import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';

export default function NotFound() {
  return (
    <Container maxWidth="sm">
      <Box sx={{ py: 8, textAlign: 'center' }}>
        <Typography variant="h1" sx={{ fontSize: '6rem', fontWeight: 700, color: 'text.secondary' }}>
          404
        </Typography>
        <Typography variant="h4" component="h1" gutterBottom>
          Page not found
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
          The page you are looking for does not exist or has been moved.
        </Typography>
        <Button variant="contained" href="/">
          Go to homepage
        </Button>
      </Box>
    </Container>
  );
}
