'use client';

import Grid from '@mui/material/Grid';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import SearchOffIcon from '@mui/icons-material/SearchOff';
import type { ApiCatalogItem } from '@apic-vibe-portal/shared';
import type { ViewMode } from './ViewToggle';
import ApiCard from './ApiCard';

export interface ApiCatalogGridProps {
  items: ApiCatalogItem[];
  viewMode: ViewMode;
}

export default function ApiCatalogGrid({ items, viewMode }: ApiCatalogGridProps) {
  if (items.length === 0) {
    return (
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          py: 8,
          gap: 2,
        }}
        data-testid="catalog-empty-state"
      >
        <SearchOffIcon sx={{ fontSize: 64, color: 'text.secondary' }} />
        <Typography variant="h6" color="text.secondary">
          No APIs found
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Try adjusting your filters or search criteria.
        </Typography>
      </Box>
    );
  }

  if (viewMode === 'list') {
    return (
      <Box data-testid="catalog-list">
        {items.map((api) => (
          <ApiCard key={api.id} api={api} listMode />
        ))}
      </Box>
    );
  }

  return (
    <Grid container spacing={3} data-testid="catalog-grid">
      {items.map((api) => (
        <Grid key={api.id} size={{ xs: 12, sm: 6, md: 4 }}>
          <ApiCard api={api} />
        </Grid>
      ))}
    </Grid>
  );
}
