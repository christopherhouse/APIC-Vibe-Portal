'use client';

import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Pagination from '@mui/material/Pagination';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Select, { type SelectChangeEvent } from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import type { PaginationMeta } from '@apic-vibe-portal/shared';

const PAGE_SIZE_OPTIONS = [10, 20, 50];

export interface CatalogPaginationProps {
  pagination: PaginationMeta;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
}

export default function CatalogPagination({
  pagination,
  onPageChange,
  onPageSizeChange,
}: CatalogPaginationProps) {
  const { page, pageSize, totalCount, totalPages } = pagination;
  const startItem = totalCount === 0 ? 0 : (page - 1) * pageSize + 1;
  const endItem = Math.min(page * pageSize, totalCount);

  const handlePageChange = (_event: React.ChangeEvent<unknown>, value: number) => {
    onPageChange(value);
  };

  const handlePageSizeChange = (event: SelectChangeEvent) => {
    onPageSizeChange(Number(event.target.value));
  };

  if (totalCount === 0) return null;

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 2,
        py: 2,
      }}
    >
      <Typography variant="body2" color="text.secondary" data-testid="pagination-info">
        Showing {startItem}–{endItem} of {totalCount} APIs
      </Typography>

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <FormControl size="small" sx={{ minWidth: 100 }}>
          <InputLabel id="page-size-label">Per page</InputLabel>
          <Select
            labelId="page-size-label"
            id="page-size-select"
            value={String(pageSize)}
            label="Per page"
            onChange={handlePageSizeChange}
          >
            {PAGE_SIZE_OPTIONS.map((size) => (
              <MenuItem key={size} value={String(size)}>
                {size}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <Pagination
          count={totalPages}
          page={page}
          onChange={handlePageChange}
          color="primary"
          showFirstButton
          showLastButton
          shape="rounded"
        />
      </Box>
    </Box>
  );
}
