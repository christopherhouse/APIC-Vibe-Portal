import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';

export default function HomePage() {
  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom>
          Welcome to APIC Vibe Portal
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Discover, understand, and use APIs faster with AI-powered assistance.
        </Typography>
      </Box>
    </Container>
  );
}
