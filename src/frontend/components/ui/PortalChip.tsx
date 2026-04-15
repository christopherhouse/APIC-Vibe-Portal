'use client';

import MuiChip, { ChipProps as MuiChipProps } from '@mui/material/Chip';

/** Lifecycle status variants for API display. */
export type LifecycleStatus = 'active' | 'deprecated' | 'preview' | 'retired';

const statusColorMap: Record<LifecycleStatus, MuiChipProps['color']> = {
  active: 'success',
  deprecated: 'warning',
  preview: 'info',
  retired: 'error',
};

export interface PortalChipProps extends Omit<MuiChipProps, 'color'> {
  /** Map a lifecycle status to a color. Overrides the `color` prop. */
  status?: LifecycleStatus;
  /** MUI Chip color (used when `status` is not provided). */
  color?: MuiChipProps['color'];
}

/**
 * Portal Chip — wraps MUI Chip with color-coded lifecycle status variants.
 */
export default function PortalChip({ status, color, ...props }: PortalChipProps) {
  const resolvedColor = status ? statusColorMap[status] : color;
  return <MuiChip color={resolvedColor} size="small" {...props} />;
}
