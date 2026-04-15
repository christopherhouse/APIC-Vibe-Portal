'use client';

import MuiCard, { CardProps as MuiCardProps } from '@mui/material/Card';
import CardHeader from '@mui/material/CardHeader';
import CardContent from '@mui/material/CardContent';
import CardActions from '@mui/material/CardActions';

export interface PortalCardProps extends MuiCardProps {
  /** Card title displayed in the header. */
  title?: string;
  /** Card subtitle displayed below the title. */
  subheader?: string;
  /** Actions rendered at the bottom of the card. */
  actions?: React.ReactNode;
}

/**
 * Portal Card — wraps MUI Card with header, content, and actions sections.
 */
export default function PortalCard({
  title,
  subheader,
  actions,
  children,
  ...props
}: PortalCardProps) {
  return (
    <MuiCard {...props}>
      {(title || subheader) && <CardHeader title={title} subheader={subheader} />}
      <CardContent>{children}</CardContent>
      {actions && <CardActions>{actions}</CardActions>}
    </MuiCard>
  );
}
