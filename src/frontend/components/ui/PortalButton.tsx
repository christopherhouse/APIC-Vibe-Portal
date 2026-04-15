'use client';

import MuiButton, { ButtonProps as MuiButtonProps } from '@mui/material/Button';

export interface PortalButtonProps extends MuiButtonProps {
  /** Show a loading spinner inside the button. */
  loading?: boolean;
}

/**
 * Portal Button — wraps MUI Button with a loading state.
 * In MUI v9, Button natively supports the loading prop.
 */
export default function PortalButton({ loading, ...props }: PortalButtonProps) {
  return <MuiButton loading={loading} {...props} />;
}
