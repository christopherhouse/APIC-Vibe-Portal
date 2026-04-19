'use client';

/**
 * Delete confirmation dialog for an API access policy.
 */

import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogActions from '@mui/material/DialogActions';

export interface DeletePolicyDialogProps {
  open: boolean;
  apiName: string;
  onClose: () => void;
  onConfirm: () => Promise<void>;
  isDeleting: boolean;
}

export default function DeletePolicyDialog({
  open,
  apiName,
  onClose,
  onConfirm,
  isDeleting,
}: DeletePolicyDialogProps) {
  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="xs"
      fullWidth
      aria-labelledby="delete-policy-dialog-title"
    >
      <DialogTitle id="delete-policy-dialog-title">Delete Access Policy</DialogTitle>
      <DialogContent>
        <DialogContentText>
          Delete the access policy for <strong>{apiName}</strong>? The API will become publicly
          accessible to all authenticated users.
        </DialogContentText>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} disabled={isDeleting}>
          Cancel
        </Button>
        <Button
          variant="contained"
          color="error"
          onClick={() => void onConfirm()}
          disabled={isDeleting}
          data-testid="confirm-delete-button"
        >
          {isDeleting ? 'Deleting…' : 'Delete'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
