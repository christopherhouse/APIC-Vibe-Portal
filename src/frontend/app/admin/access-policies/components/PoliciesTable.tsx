'use client';

/**
 * Table displaying all API access policies.
 */

import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import IconButton from '@mui/material/IconButton';
import Chip from '@mui/material/Chip';
import Tooltip from '@mui/material/Tooltip';
import Box from '@mui/material/Box';
import Skeleton from '@mui/material/Skeleton';
import Typography from '@mui/material/Typography';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import LockOpenIcon from '@mui/icons-material/LockOpen';
import GroupIcon from '@mui/icons-material/Group';
import type { AccessPolicy } from '@/lib/admin-api';

export interface PoliciesTableProps {
  policies: AccessPolicy[];
  isLoading: boolean;
  onEdit: (policy: AccessPolicy) => void;
  onDelete: (policy: AccessPolicy) => void;
}

export default function PoliciesTable({
  policies,
  isLoading,
  onEdit,
  onDelete,
}: PoliciesTableProps) {
  if (isLoading) {
    return (
      <Box data-testid="policies-table-skeleton">
        {Array.from({ length: 4 }, (_, i) => (
          <Skeleton key={i} variant="rounded" height={52} sx={{ mb: 1 }} />
        ))}
      </Box>
    );
  }

  if (policies.length === 0) {
    return (
      <Box
        data-testid="policies-empty-state"
        sx={{ textAlign: 'center', py: 6, color: 'text.secondary' }}
      >
        <LockOpenIcon sx={{ fontSize: 48, mb: 2, opacity: 0.4 }} />
        <Typography variant="h6">No access policies configured</Typography>
        <Typography variant="body2">
          All APIs are publicly accessible to authenticated users. Create a policy to restrict
          access to specific groups.
        </Typography>
      </Box>
    );
  }

  return (
    <TableContainer component={Paper} variant="outlined" data-testid="policies-table">
      <Table aria-label="API access policies">
        <TableHead>
          <TableRow>
            <TableCell>API Name</TableCell>
            <TableCell>Access</TableCell>
            <TableCell>Allowed Groups</TableCell>
            <TableCell>Last Updated</TableCell>
            <TableCell align="right">Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {policies.map((policy) => (
            <TableRow key={policy.apiName} hover data-testid={`policy-row-${policy.apiName}`}>
              <TableCell>
                <Typography variant="body2" sx={{ fontWeight: 500 }}>
                  {policy.apiName}
                </Typography>
              </TableCell>

              <TableCell>
                {policy.isPublic ? (
                  <Chip
                    icon={<LockOpenIcon />}
                    label="Public"
                    color="success"
                    size="small"
                    variant="outlined"
                  />
                ) : (
                  <Chip
                    icon={<GroupIcon />}
                    label="Restricted"
                    color="warning"
                    size="small"
                    variant="outlined"
                  />
                )}
              </TableCell>

              <TableCell>
                {policy.isPublic ? (
                  <Typography variant="body2" color="text.secondary">
                    All authenticated users
                  </Typography>
                ) : policy.allowedGroups.length === 0 ? (
                  <Typography variant="body2" color="error">
                    No groups — API inaccessible
                  </Typography>
                ) : (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {policy.allowedGroups.map((g) => (
                      <Chip
                        key={g}
                        label={g}
                        size="small"
                        sx={{ fontFamily: 'monospace', fontSize: '0.7rem' }}
                      />
                    ))}
                  </Box>
                )}
              </TableCell>

              <TableCell>
                <Typography variant="body2" color="text.secondary">
                  {policy.updatedAt ? new Date(policy.updatedAt).toLocaleDateString() : '—'}
                </Typography>
              </TableCell>

              <TableCell align="right">
                <Tooltip title="Edit policy">
                  <IconButton
                    size="small"
                    onClick={() => onEdit(policy)}
                    aria-label={`Edit policy for ${policy.apiName}`}
                    data-testid={`edit-policy-${policy.apiName}`}
                  >
                    <EditIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
                <Tooltip title="Delete policy (API becomes public)">
                  <IconButton
                    size="small"
                    color="error"
                    onClick={() => onDelete(policy)}
                    aria-label={`Delete policy for ${policy.apiName}`}
                    data-testid={`delete-policy-${policy.apiName}`}
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
