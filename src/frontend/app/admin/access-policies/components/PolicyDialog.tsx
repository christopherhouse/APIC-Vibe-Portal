'use client';

/**
 * Dialog for creating or editing an API access policy.
 *
 * Handles both "create new" (apiName editable) and "edit existing"
 * (apiName fixed) modes.  In create mode, the API name is selected
 * from a searchable dropdown of available APIs fetched from the catalog.
 */

import { useEffect, useState } from 'react';
import Autocomplete from '@mui/material/Autocomplete';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import TextField from '@mui/material/TextField';
import FormControlLabel from '@mui/material/FormControlLabel';
import Switch from '@mui/material/Switch';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Alert from '@mui/material/Alert';
import AddIcon from '@mui/icons-material/Add';
import type { AccessPolicy, AccessPolicyRequest } from '@/lib/admin-api';

/** Minimal API summary for the dropdown options. */
export interface ApiOption {
  name: string;
  title: string;
}

export interface PolicyDialogProps {
  open: boolean;
  /** When provided, the dialog is in edit mode; otherwise create mode. */
  existing?: AccessPolicy | null;
  /** Available APIs to select from in the dropdown (create mode). */
  availableApis?: ApiOption[];
  /** Whether the available APIs are still loading. */
  apisLoading?: boolean;
  onClose: () => void;
  onSave: (apiName: string, request: AccessPolicyRequest) => Promise<void>;
}

export default function PolicyDialog({
  open,
  existing,
  availableApis = [],
  apisLoading = false,
  onClose,
  onSave,
}: PolicyDialogProps) {
  const isEdit = Boolean(existing);

  const [apiName, setApiName] = useState('');
  const [isPublic, setIsPublic] = useState(false);
  const [groupInput, setGroupInput] = useState('');
  const [allowedGroups, setAllowedGroups] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Populate form when editing an existing policy
  useEffect(() => {
    if (open) {
      setApiName(existing?.apiName ?? '');
      setIsPublic(existing?.isPublic ?? false);
      setAllowedGroups(existing?.allowedGroups ?? []);
      setGroupInput('');
      setError(null);
    }
  }, [open, existing]);

  const handleAddGroup = () => {
    const trimmed = groupInput.trim();
    if (trimmed && !allowedGroups.includes(trimmed)) {
      setAllowedGroups((prev) => [...prev, trimmed]);
    }
    setGroupInput('');
  };

  const handleGroupKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddGroup();
    }
  };

  const handleRemoveGroup = (group: string) => {
    setAllowedGroups((prev) => prev.filter((g) => g !== group));
  };

  const handleSave = async () => {
    if (!apiName.trim()) {
      setError('API name is required.');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onSave(apiName.trim(), { allowedGroups, isPublic });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save policy.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      aria-labelledby="policy-dialog-title"
    >
      <DialogTitle id="policy-dialog-title">
        {isEdit ? `Edit Policy: ${existing?.apiName}` : 'New Access Policy'}
      </DialogTitle>

      <DialogContent>
        <Stack spacing={3} sx={{ mt: 1 }}>
          {error && <Alert severity="error">{error}</Alert>}

          {isEdit ? (
            <TextField
              label="API Name"
              value={apiName}
              disabled
              fullWidth
              helperText="The API name cannot be changed after creation."
              slotProps={{ htmlInput: { 'data-testid': 'api-name-input' } }}
            />
          ) : (
            <Autocomplete
              options={availableApis}
              getOptionLabel={(option) =>
                option.title ? `${option.title} (${option.name})` : option.name
              }
              value={availableApis.find((a) => a.name === apiName) ?? null}
              onChange={(_event, newValue) => setApiName(newValue?.name ?? '')}
              loading={apisLoading}
              isOptionEqualToValue={(option, value) => option.name === value.name}
              data-testid="api-name-autocomplete"
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="API Name"
                  required
                  helperText="Select the API from the catalog."
                />
              )}
            />
          )}

          <FormControlLabel
            control={
              <Switch
                checked={isPublic}
                onChange={(e) => setIsPublic(e.target.checked)}
                data-testid="is-public-switch"
              />
            }
            label="Public (all authenticated users can access)"
          />

          {!isPublic && (
            <>
              <Typography variant="body2" color="text.secondary">
                Allowed Groups — enter Entra ID group object IDs (OIDs) whose members may access
                this API. Press Enter or click Add after each OID.
              </Typography>

              <Stack direction="row" spacing={1}>
                <TextField
                  label="Group OID"
                  value={groupInput}
                  onChange={(e) => setGroupInput(e.target.value)}
                  onKeyDown={handleGroupKeyDown}
                  size="small"
                  fullWidth
                  slotProps={{ htmlInput: { 'data-testid': 'group-oid-input' } }}
                />
                <Button
                  variant="outlined"
                  startIcon={<AddIcon />}
                  onClick={handleAddGroup}
                  disabled={!groupInput.trim()}
                  data-testid="add-group-button"
                  sx={{ whiteSpace: 'nowrap' }}
                >
                  Add
                </Button>
              </Stack>

              {allowedGroups.length > 0 && (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {allowedGroups.map((g) => (
                    <Chip
                      key={g}
                      label={g}
                      onDelete={() => handleRemoveGroup(g)}
                      size="small"
                      data-testid={`group-chip-${g}`}
                    />
                  ))}
                </Box>
              )}

              {allowedGroups.length === 0 && (
                <Alert severity="warning">
                  No groups added. This API will be inaccessible to all non-admin users.
                </Alert>
              )}
            </>
          )}
        </Stack>
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} disabled={saving}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={() => void handleSave()}
          disabled={saving || !apiName.trim()}
          data-testid="save-policy-button"
        >
          {saving ? 'Saving…' : 'Save Policy'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
