'use client';

import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import Link from '@mui/material/Link';
import Skeleton from '@mui/material/Skeleton';
import type { ApiDeployment } from '@apic-vibe-portal/shared';
import { formatDate } from '@/lib/utils';

export interface ApiDeploymentsProps {
  deployments: ApiDeployment[];
  isLoading?: boolean;
}

export default function ApiDeployments({ deployments, isLoading }: ApiDeploymentsProps) {
  if (isLoading) {
    return (
      <Box data-testid="deployments-skeleton">
        <Skeleton variant="rounded" height={200} />
      </Box>
    );
  }

  if (deployments.length === 0) {
    return (
      <Box data-testid="deployments-empty">
        <Typography variant="body1" color="text.secondary">
          No deployments found for this API.
        </Typography>
      </Box>
    );
  }

  return (
    <Box data-testid="deployments-table">
      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 600 }}>Deployment</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Environment</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Server URL</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Updated</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {deployments.map((deployment) => (
              <TableRow key={deployment.id} data-testid={`deployment-row-${deployment.id}`}>
                <TableCell>
                  <Typography variant="body2">{deployment.title}</Typography>
                </TableCell>
                <TableCell>
                  <Chip label={deployment.environment.title} size="small" variant="outlined" />
                </TableCell>
                <TableCell>
                  {deployment.server.runtimeUri.map((uri, idx) => (
                    <Box key={idx}>
                      <Link href={uri} target="_blank" rel="noopener" variant="body2">
                        {uri}
                      </Link>
                    </Box>
                  ))}
                </TableCell>
                <TableCell>
                  <Typography variant="body2" color="text.secondary">
                    {formatDate(deployment.updatedAt)}
                  </Typography>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
