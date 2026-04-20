'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  Box,
  Container,
  Typography,
  Alert,
  CircularProgress,
  Button,
  Card,
  CardContent,
  Chip,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { fetchApiCompliance, type ApiCompliance } from '@/lib/governance-api';

export default function ApiCompliancePage() {
  const params = useParams<{ apiId: string }>();
  const apiId = params.apiId;
  const router = useRouter();
  const [compliance, setCompliance] = useState<ApiCompliance | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadCompliance() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchApiCompliance(apiId);
        setCompliance(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load compliance data');
      } finally {
        setLoading(false);
      }
    }

    loadCompliance();
  }, [apiId]);

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      </Container>
    );
  }

  if (error || !compliance) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Alert severity="error">{error || 'No compliance data available'}</Alert>
      </Container>
    );
  }

  const getCategoryColor = (
    category: string
  ): 'success' | 'primary' | 'warning' | 'error' | 'default' => {
    switch (category) {
      case 'Excellent':
        return 'success';
      case 'Good':
        return 'primary';
      case 'Needs Improvement':
        return 'warning';
      case 'Poor':
        return 'error';
      default:
        return 'default';
    }
  };

  const failingRules = compliance.findings.filter((f) => !f.passed);
  const passingRules = compliance.findings.filter((f) => f.passed);

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }} data-testid="api-compliance-detail">
      <Button
        startIcon={<ArrowBackIcon />}
        onClick={() => router.push('/governance')}
        sx={{ mb: 2 }}
      >
        Back to Dashboard
      </Button>

      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Typography variant="h4" gutterBottom>
            {compliance.apiName}
          </Typography>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', mb: 2 }}>
            <Typography variant="h2" component="div">
              {compliance.score.toFixed(1)}
            </Typography>
            <Chip label={compliance.category} color={getCategoryColor(compliance.category)} />
          </Box>
          <Typography variant="body2" color="text.secondary">
            {compliance.criticalFailures} critical failure(s) • Last checked:{' '}
            {new Date(compliance.lastChecked).toLocaleString()}
          </Typography>
        </CardContent>
      </Card>

      {failingRules.length > 0 && (
        <Box sx={{ mb: 4 }}>
          <Typography variant="h5" gutterBottom>
            Failing Rules ({failingRules.length})
          </Typography>
          {failingRules.map((finding) => (
            <Accordion key={finding.ruleId} data-testid={`failing-rule-${finding.ruleId}`}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                  <ErrorIcon color="error" />
                  <Typography sx={{ flexGrow: 1 }}>{finding.ruleName}</Typography>
                  <Chip label={finding.severity} color="error" size="small" />
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <Typography variant="body2" sx={{ mb: 2 }}>
                  {finding.message}
                </Typography>
                <Typography variant="subtitle2" gutterBottom>
                  Remediation:
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {finding.remediation}
                </Typography>
              </AccordionDetails>
            </Accordion>
          ))}
        </Box>
      )}

      <Box>
        <Typography variant="h5" gutterBottom>
          Passing Rules ({passingRules.length})
        </Typography>
        <List>
          {passingRules.map((finding) => (
            <ListItem key={finding.ruleId} data-testid={`passing-rule-${finding.ruleId}`}>
              <ListItemIcon>
                <CheckCircleIcon color="success" />
              </ListItemIcon>
              <ListItemText
                primary={finding.ruleName}
                secondary={
                  <Chip label={finding.severity} color="default" size="small" sx={{ ml: 1 }} />
                }
              />
            </ListItem>
          ))}
        </List>
      </Box>
    </Container>
  );
}
