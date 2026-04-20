'use client';

import TableRow from '@mui/material/TableRow';
import TableCell from '@mui/material/TableCell';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import type { AspectComparison } from '@/lib/compare-api';

export interface CompareAspectRowProps {
  row: AspectComparison;
}

export default function CompareAspectRow({ row }: CompareAspectRowProps) {
  return (
    <TableRow
      data-testid={`aspect-row-${row.aspect}`}
      sx={row.allEqual ? {} : { backgroundColor: 'action.hover' }}
    >
      {/* Label column */}
      <TableCell
        component="th"
        scope="row"
        sx={{ fontWeight: 600, whiteSpace: 'nowrap', minWidth: 160 }}
      >
        {row.label}
      </TableCell>

      {/* One value cell per API */}
      {row.values.map((val, index) => (
        <TableCell key={index} align="center" data-testid={`aspect-value-${row.aspect}-${index}`}>
          {val.isBest ? (
            <Chip
              label={val.display ?? val.value ?? '—'}
              color="success"
              size="small"
              variant="outlined"
            />
          ) : (
            <Typography variant="body2" color={val.value ? 'text.primary' : 'text.disabled'}>
              {val.display ?? val.value ?? '—'}
            </Typography>
          )}
        </TableCell>
      ))}
    </TableRow>
  );
}
