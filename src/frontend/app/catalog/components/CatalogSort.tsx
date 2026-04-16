'use client';

import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Select, { type SelectChangeEvent } from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';

export type SortField = 'name' | 'updatedAt' | 'createdAt';
export type SortDirection = 'asc' | 'desc';

const SORT_OPTIONS: { value: string; label: string }[] = [
  { value: 'updatedAt:desc', label: 'Last Updated (newest)' },
  { value: 'updatedAt:asc', label: 'Last Updated (oldest)' },
  { value: 'name:asc', label: 'Name (A–Z)' },
  { value: 'name:desc', label: 'Name (Z–A)' },
  { value: 'createdAt:desc', label: 'Created (newest)' },
  { value: 'createdAt:asc', label: 'Created (oldest)' },
];

export interface CatalogSortProps {
  sort: SortField;
  direction: SortDirection;
  onSortChange: (sort: SortField, direction: SortDirection) => void;
}

export default function CatalogSort({ sort, direction, onSortChange }: CatalogSortProps) {
  const currentValue = `${sort}:${direction}`;

  const handleChange = (event: SelectChangeEvent) => {
    const [field, dir] = event.target.value.split(':') as [SortField, SortDirection];
    onSortChange(field, dir);
  };

  return (
    <FormControl size="small" sx={{ minWidth: 200 }}>
      <InputLabel id="catalog-sort-label">Sort by</InputLabel>
      <Select
        labelId="catalog-sort-label"
        id="catalog-sort"
        value={currentValue}
        label="Sort by"
        onChange={handleChange}
      >
        {SORT_OPTIONS.map((opt) => (
          <MenuItem key={opt.value} value={opt.value}>
            {opt.label}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
}
