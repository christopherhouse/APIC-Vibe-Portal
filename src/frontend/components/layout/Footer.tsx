import Box from '@mui/material/Box';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';

export default function Footer() {
  return (
    <Box
      component="footer"
      sx={{
        py: 1.5,
        px: 2,
        mt: 'auto',
        backgroundColor: 'background.paper',
        borderTop: '1px solid',
        borderColor: 'divider',
        height: 'var(--footer-height)',
        display: 'flex',
        alignItems: 'center',
      }}
    >
      <Container maxWidth="lg">
        <Typography variant="body2" color="text.secondary" align="center">
          © {new Date().getFullYear()} APIC Vibe Portal — Powered by Azure API Center
        </Typography>
      </Container>
    </Box>
  );
}
