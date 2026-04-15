'use client';

import MuiTextField, { TextFieldProps as MuiTextFieldProps } from '@mui/material/TextField';

export type PortalTextFieldProps = MuiTextFieldProps;

/**
 * Portal TextField — wraps MUI TextField with portal defaults.
 * Provides label, error state, and helper text out of the box.
 */
export default function PortalTextField(props: PortalTextFieldProps) {
  return <MuiTextField fullWidth {...props} />;
}
