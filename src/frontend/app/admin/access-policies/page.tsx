'use client';

/**
 * Admin — API Access Policies management page.
 *
 * Only accessible to users with the `Portal.Admin` role.  Non-admin users
 * are shown a 403 message.
 *
 * Allows admins to:
 * - View all configured access policies
 * - Create a new policy (restrict an API to specific Entra ID groups)
 * - Edit an existing policy (change groups or toggle isPublic)
 * - Delete a policy (API reverts to publicly accessible)
 * - Force-refresh the BFF in-memory policy cache
 */

import { useCallback, useEffect, useState } from 'react';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Alert from '@mui/material/Alert';
import Snackbar from '@mui/material/Snackbar';
import Tooltip from '@mui/material/Tooltip';
import Stack from '@mui/material/Stack';
import AddIcon from '@mui/icons-material/Add';
import RefreshIcon from '@mui/icons-material/Refresh';
import BlockIcon from '@mui/icons-material/Block';

import { useAuth } from '@/lib/auth/use-auth';
import {
  fetchAccessPolicies,
  upsertAccessPolicy,
  deleteAccessPolicy,
  invalidatePolicyCache,
  type AccessPolicy,
  type AccessPolicyRequest,
} from '@/lib/admin-api';
import { fetchCatalogApis } from '@/lib/catalog-api';

import PoliciesTable from './components/PoliciesTable';
import PolicyDialog from './components/PolicyDialog';
import type { ApiOption } from './components/PolicyDialog';
import DeletePolicyDialog from './components/DeletePolicyDialog';

const ADMIN_ROLE = 'Portal.Admin';

export default function AccessPoliciesPage() {
  const { user, isAuthenticated } = useAuth();
  const isAdmin = Boolean(user?.roles.includes(ADMIN_ROLE));

  const [policies, setPolicies] = useState<AccessPolicy[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Create/Edit dialog state
  const [policyDialogOpen, setPolicyDialogOpen] = useState(false);
  const [editingPolicy, setEditingPolicy] = useState<AccessPolicy | null>(null);

  // Delete dialog state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deletingPolicy, setDeletingPolicy] = useState<AccessPolicy | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Available APIs for the policy dialog dropdown
  const [availableApis, setAvailableApis] = useState<ApiOption[]>([]);
  const [apisLoading, setApisLoading] = useState(false);

  // Success / error toast
  const [snackbar, setSnackbar] = useState<{
    message: string;
    severity: 'success' | 'error';
  } | null>(null);

  // ---------------------------------------------------------------------------
  // Data loading
  // ---------------------------------------------------------------------------

  const loadPolicies = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const data = await fetchAccessPolicies();
      setPolicies(data);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to load policies.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadAvailableApis = useCallback(async () => {
    setApisLoading(true);
    try {
      const response = await fetchCatalogApis({ pageSize: 100 });
      setAvailableApis(response.data.map((api) => ({ name: api.name, title: api.title })));
    } catch (err) {
      // Non-critical: admin can still manage policies without the dropdown.
      console.warn('Failed to load available APIs for policy dropdown:', err);
    } finally {
      setApisLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated && isAdmin) {
      void loadPolicies();
      void loadAvailableApis();
    } else {
      setIsLoading(false);
    }
  }, [isAuthenticated, isAdmin, loadPolicies, loadAvailableApis]);

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  const handleCreate = () => {
    setEditingPolicy(null);
    setPolicyDialogOpen(true);
  };

  const handleEdit = (policy: AccessPolicy) => {
    setEditingPolicy(policy);
    setPolicyDialogOpen(true);
  };

  const handleSavePolicy = async (apiName: string, request: AccessPolicyRequest) => {
    await upsertAccessPolicy(apiName, request);
    setSnackbar({ message: `Policy for "${apiName}" saved.`, severity: 'success' });
    await loadPolicies();
  };

  const handleDeleteIntent = (policy: AccessPolicy) => {
    setDeletingPolicy(policy);
    setDeleteDialogOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!deletingPolicy) return;
    setIsDeleting(true);
    try {
      await deleteAccessPolicy(deletingPolicy.apiName);
      setSnackbar({
        message: `Policy for "${deletingPolicy.apiName}" deleted. The API is now public.`,
        severity: 'success',
      });
      setDeleteDialogOpen(false);
      await loadPolicies();
    } catch (err) {
      setSnackbar({
        message: err instanceof Error ? err.message : 'Failed to delete policy.',
        severity: 'error',
      });
    } finally {
      setIsDeleting(false);
    }
  };

  const handleRefreshCache = async () => {
    try {
      await invalidatePolicyCache();
      setSnackbar({ message: 'Policy cache refreshed on the server.', severity: 'success' });
    } catch (err) {
      setSnackbar({
        message: err instanceof Error ? err.message : 'Failed to refresh cache.',
        severity: 'error',
      });
    }
  };

  // ---------------------------------------------------------------------------
  // Access guard
  // ---------------------------------------------------------------------------

  if (!isAdmin && !isLoading) {
    return (
      <Container maxWidth="sm" sx={{ py: 8, textAlign: 'center' }}>
        <BlockIcon sx={{ fontSize: 64, color: 'error.main', mb: 2 }} />
        <Typography variant="h5" gutterBottom>
          Access Denied
        </Typography>
        <Typography variant="body1" color="text.secondary">
          You need the <strong>Portal.Admin</strong> role to manage API access policies.
        </Typography>
      </Container>
    );
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <Container maxWidth="xl" sx={{ py: 2 }}>
      {/* Page header */}
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        spacing={2}
        sx={{ mb: 3, alignItems: { sm: 'center' } }}
      >
        <Box sx={{ flex: 1 }}>
          <Typography variant="h4" component="h1" gutterBottom>
            API Access Policies
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Control which Entra ID groups can access each API. APIs without a policy are publicly
            accessible to all authenticated users.
          </Typography>
        </Box>
        <Stack direction="row" spacing={1}>
          <Tooltip title="Force-refresh the BFF policy cache">
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={() => void handleRefreshCache()}
              data-testid="refresh-cache-button"
            >
              Refresh Cache
            </Button>
          </Tooltip>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleCreate}
            data-testid="add-policy-button"
          >
            New Policy
          </Button>
        </Stack>
      </Stack>

      {/* Load error */}
      {loadError && (
        <Alert severity="error" sx={{ mb: 2 }} data-testid="load-error">
          {loadError}
        </Alert>
      )}

      {/* Policies table */}
      <PoliciesTable
        policies={policies}
        isLoading={isLoading}
        onEdit={handleEdit}
        onDelete={handleDeleteIntent}
      />

      {/* Create / Edit dialog */}
      <PolicyDialog
        open={policyDialogOpen}
        existing={editingPolicy}
        availableApis={availableApis}
        apisLoading={apisLoading}
        onClose={() => setPolicyDialogOpen(false)}
        onSave={handleSavePolicy}
      />

      {/* Delete confirmation dialog */}
      <DeletePolicyDialog
        open={deleteDialogOpen}
        apiName={deletingPolicy?.apiName ?? ''}
        onClose={() => setDeleteDialogOpen(false)}
        onConfirm={handleConfirmDelete}
        isDeleting={isDeleting}
      />

      {/* Success / error toast */}
      <Snackbar
        open={Boolean(snackbar)}
        autoHideDuration={4000}
        onClose={() => setSnackbar(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        {snackbar ? (
          <Alert
            onClose={() => setSnackbar(null)}
            severity={snackbar.severity}
            variant="filled"
            data-testid="snackbar-alert"
          >
            {snackbar.message}
          </Alert>
        ) : (
          <span />
        )}
      </Snackbar>
    </Container>
  );
}
