'use client';

import MuiSkeleton, { SkeletonProps as MuiSkeletonProps } from '@mui/material/Skeleton';
import Box from '@mui/material/Box';

export interface PortalSkeletonProps extends MuiSkeletonProps {
  /** Number of skeleton lines to render. */
  lines?: number;
}

/**
 * Portal Skeleton — wraps MUI Skeleton with multi-line support for loading placeholders.
 */
export default function PortalSkeleton({ lines = 1, ...props }: PortalSkeletonProps) {
  if (lines <= 1) {
    return <MuiSkeleton {...props} />;
  }

  return (
    <Box>
      {Array.from({ length: lines }, (_, i) => (
        <MuiSkeleton
          key={i}
          {...props}
          sx={{
            mb: 1,
            ...(i === lines - 1 ? { width: '60%' } : {}),
            ...(props.sx ?? {}),
          }}
        />
      ))}
    </Box>
  );
}
