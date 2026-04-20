'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
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
import { fetchSuggestions } from '@/lib/search-api';

const MAX_COMPARE = 5;
const MIN_COMPARE = 2;
const DEBOUNCE_MS = 300;

export interface CompareSelectorProps {
  selectedIds: string[];
  onAdd: (api: ApiCatalogItem) => void;
  onRemove: (id: string) => void;
}

/** Minimal catalog-item shape built from a suggest result. */
function suggestToItem(s: {
  apiId: string;
  title: string;
  description: string;
  kind: string;
}): ApiCatalogItem {
  return {
    id: s.apiId,
    name: s.apiId,
    title: s.title,
    description: s.description,
    kind: s.kind as ApiCatalogItem['kind'],
    lifecycleStage: 'production' as ApiCatalogItem['lifecycleStage'],
    versionCount: 0,
    deploymentCount: 0,
    updatedAt: '',
  };
}

export default function CompareSelector({ selectedIds, onAdd, onRemove }: CompareSelectorProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<ApiCatalogItem[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const abortControllerRef = useRef<AbortController | null>(null);
  // Incremented each time a new search starts; used to discard stale responses.
  const requestIdRef = useRef(0);

  // Clear pending timer and in-flight request on unmount
  useEffect(() => {
    return () => {
      clearTimeout(debounceTimerRef.current);
      abortControllerRef.current?.abort();
    };
  }, []);

  const search = useCallback(async (q: string) => {
    // Abort any in-flight request and start a fresh one
    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;

    const requestId = ++requestIdRef.current;

    if (!q.trim()) {
      setResults([]);
      setIsSearching(false);
      return;
    }

    setIsSearching(true);
    try {
      const resp = await fetchSuggestions(q, controller.signal);
      // Discard stale responses from earlier queries
      if (requestId !== requestIdRef.current) return;
      setResults(resp.suggestions.map(suggestToItem));
    } catch (err) {
      if ((err as Error).name === 'AbortError') return;
      setResults([]);
    } finally {
      if (requestId === requestIdRef.current) {
        setIsSearching(false);
      }
    }
  }, []);

  const handleInputChange = (value: string) => {
    setQuery(value);
    clearTimeout(debounceTimerRef.current);
    debounceTimerRef.current = setTimeout(() => void search(value), DEBOUNCE_MS);
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
            slotProps={{
              htmlInput: { 'data-testid': 'compare-search-input' },
              input: {
                endAdornment: isSearching ? <CircularProgress size={16} /> : undefined,
              },
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
