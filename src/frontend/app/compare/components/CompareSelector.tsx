'use client';

import { useState, useCallback } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import Chip from '@mui/material/Chip';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemText from '@mui/material/ListItemText';
import Paper from '@mui/material/Paper';
import Divider from '@mui/material/Divider';
import CircularProgress from '@mui/material/CircularProgress';
import type { ApiCatalogItem } from '@apic-vibe-portal/shared';
import { fetchCatalogApis } from '@/lib/catalog-api';

const MAX_COMPARE = 5;
const MIN_COMPARE = 2;

export interface CompareSelectorProps {
  selectedIds: string[];
  onAdd: (api: ApiCatalogItem) => void;
  onRemove: (id: string) => void;
}

export default function CompareSelector({ selectedIds, onAdd, onRemove }: CompareSelectorProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<ApiCatalogItem[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const debounceRef = useCallback(
    (() => {
      let timer: ReturnType<typeof setTimeout>;
      return (fn: () => void, ms: number) => {
        clearTimeout(timer);
        timer = setTimeout(fn, ms);
      };
    })(),
    []
  );

  const search = useCallback(async (q: string) => {
    if (!q.trim()) {
      setResults([]);
      return;
    }
    setIsSearching(true);
    try {
      const resp = await fetchCatalogApis({ pageSize: 10 });
      const filtered = resp.data.filter(
        (api) =>
          api.title.toLowerCase().includes(q.toLowerCase()) ||
          api.name.toLowerCase().includes(q.toLowerCase())
      );
      setResults(filtered);
    } catch {
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  }, []);

  const handleInputChange = (value: string) => {
    setQuery(value);
    debounceRef(() => void search(value), 300);
  };

  const canAddMore = selectedIds.length < MAX_COMPARE;

  return (
    <Box data-testid="compare-selector">
      <Typography variant="subtitle2" gutterBottom>
        Selected APIs ({selectedIds.length}/{MAX_COMPARE})
        {selectedIds.length < MIN_COMPARE && (
          <Typography component="span" variant="caption" color="warning.main" sx={{ ml: 1 }}>
            — select at least {MIN_COMPARE - selectedIds.length} more
          </Typography>
        )}
      </Typography>

      {/* Selected chips */}
      {selectedIds.length > 0 && (
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
          {selectedIds.map((id) => (
            <Chip
              key={id}
              label={id}
              onDelete={() => onRemove(id)}
              size="small"
              data-testid={`selected-chip-${id}`}
            />
          ))}
        </Box>
      )}

      {/* Search input */}
      {canAddMore && (
        <Box sx={{ position: 'relative' }}>
          <TextField
            fullWidth
            size="small"
            label="Search APIs to add"
            value={query}
            onChange={(e) => handleInputChange(e.target.value)}
            placeholder="Type API name…"
            inputProps={{ 'data-testid': 'compare-search-input' }}
            InputProps={{
              endAdornment: isSearching ? <CircularProgress size={16} /> : undefined,
            }}
          />

          {results.length > 0 && (
            <Paper
              elevation={4}
              sx={{
                position: 'absolute',
                zIndex: 10,
                width: '100%',
                maxHeight: 300,
                overflow: 'auto',
              }}
            >
              <List dense disablePadding>
                {results.map((api, index) => {
                  const alreadySelected = selectedIds.includes(api.id);
                  return (
                    <Box key={api.id}>
                      {index > 0 && <Divider />}
                      <ListItem disablePadding>
                        <ListItemButton
                          disabled={alreadySelected}
                          onClick={() => {
                            if (!alreadySelected) {
                              onAdd(api);
                              setQuery('');
                              setResults([]);
                            }
                          }}
                          data-testid={`search-result-${api.id}`}
                        >
                          <ListItemText
                            primary={api.title}
                            secondary={`${api.kind.toUpperCase()} · ${api.lifecycleStage}`}
                          />
                          {alreadySelected && (
                            <Typography variant="caption" color="text.disabled">
                              Added
                            </Typography>
                          )}
                        </ListItemButton>
                      </ListItem>
                    </Box>
                  );
                })}
              </List>
            </Paper>
          )}
        </Box>
      )}
    </Box>
  );
}
