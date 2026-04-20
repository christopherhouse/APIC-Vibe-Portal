/**
 * Agent card component for displaying agent summary in the grid.
 */

import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import CardActions from '@mui/material/CardActions';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import InfoIcon from '@mui/icons-material/Info';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';

import type { AgentInfo } from '@/lib/admin-agent-api';

interface AgentCardProps {
  agent: AgentInfo;
  onViewDetails: (agentId: string) => void;
  onTest: (agentId: string) => void;
}

export default function AgentCard({ agent, onViewDetails, onTest }: AgentCardProps) {
  const statusColor = agent.status === 'active' ? 'success' : 'default';
  const statusIcon = agent.status === 'active' ? <CheckCircleIcon fontSize="small" /> : undefined;

  return (
    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <CardContent sx={{ flex: 1 }}>
        <Stack direction="row" spacing={1} sx={{ mb: 2, alignItems: 'center' }}>
          <Typography variant="h6" component="h2" sx={{ flex: 1 }}>
            {agent.name}
          </Typography>
          <Chip
            label={agent.status}
            color={statusColor}
            size="small"
            icon={statusIcon}
            data-testid={`status-${agent.agentId}`}
          />
        </Stack>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {agent.description}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Registered: {new Date(agent.registeredAt).toLocaleDateString()}
        </Typography>
      </CardContent>
      <CardActions>
        <Button
          size="small"
          startIcon={<InfoIcon />}
          onClick={() => onViewDetails(agent.agentId)}
          data-testid={`details-${agent.agentId}`}
        >
          Details
        </Button>
        <Button
          size="small"
          startIcon={<PlayArrowIcon />}
          onClick={() => onTest(agent.agentId)}
          data-testid={`test-${agent.agentId}`}
        >
          Test
        </Button>
      </CardActions>
    </Card>
  );
}
