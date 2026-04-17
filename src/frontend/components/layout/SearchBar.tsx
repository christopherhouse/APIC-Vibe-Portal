'use client';

import { useCallback, useEffect, useRef, useState, useId } from 'react';
import { useRouter } from 'next/navigation';
import Box from '@mui/material/Box';
import InputBase from '@mui/material/InputBase';
import IconButton from '@mui/material/IconButton';
import Paper from '@mui/material/Paper';
import List from '@mui/material/List';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemText from '@mui/material/ListItemText';
import ListItemIcon from '@mui/material/ListItemIcon';
import Typography from '@mui/material/Typography';
import CircularProgress from '@mui/material/CircularProgress';
import Chip from '@mui/material/Chip';
import SearchIcon from '@mui/icons-material/Search';
import ClearIcon from '@mui/icons-material/Clear';
import ApiIcon from '@mui/icons-material/Api';
import { alpha, styled } from '@mui/material/styles';
import { useAutocomplete } from '@/hooks/use-autocomplete';

// ---------------------------------------------------------------------------
// Styled components
// ---------------------------------------------------------------------------

const SearchWrapper = styled('div')(({ theme }) => ({
  position: 'relative',
  borderRadius: theme.shape.borderRadius,
  backgroundColor: alpha(theme.palette.common.white, 0.15),
  '&:hover': { backgroundColor: alpha(theme.palette.common.white, 0.25) },
  marginRight: theme.spacing(2),
  marginLeft: theme.spacing(3),
  width: 'auto',
  flexGrow: 1,
  maxWidth: 480,
}));

const SearchIconWrapper = styled('div')(({ theme }) => ({
  padding: theme.spacing(0, 2),
  height: '100%',
  position: 'absolute',
  pointerEvents: 'none',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
}));

const StyledInput = styled(InputBase)(({ theme }) => ({
  color: 'inherit',
  width: '100%',
  '& .MuiInputBase-input': {
    padding: theme.spacing(1, 1, 1, 0),
    paddingLeft: `calc(1em + ${theme.spacing(4)})`,
    paddingRight: theme.spacing(5),
    width: '100%',
  },
}));

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/** Kind → short label for the suggestion chip. */
const KIND_LABEL: Record<string, string> = {
  rest: 'REST',
  graphql: 'GraphQL',
  grpc: 'gRPC',
  soap: 'SOAP',
  websocket: 'WS',
  webhook: 'Hook',
};

export default function SearchBar() {
  const router = useRouter();
  const listId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const [inputValue, setInputValue] = useState('');
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  const { suggestions, isLoading } = useAutocomplete({ query: inputValue });

  const showDropdown = open && (suggestions.length > 0 || isLoading);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
        setActiveIndex(-1);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const navigateToSearch = useCallback(
    (query: string) => {
      if (!query.trim()) return;
      setOpen(false);
      setActiveIndex(-1);
      router.push(`/search?q=${encodeURIComponent(query.trim())}`);
    },
    [router]
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!showDropdown) {
      if (e.key === 'Enter') navigateToSearch(inputValue);
      return;
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, suggestions.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, -1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (activeIndex >= 0 && activeIndex < suggestions.length) {
        const item = suggestions[activeIndex];
        setOpen(false);
        setActiveIndex(-1);
        setInputValue(item.title);
        router.push(`/catalog/${item.apiId}`);
      } else {
        navigateToSearch(inputValue);
      }
    } else if (e.key === 'Escape') {
      setOpen(false);
      setActiveIndex(-1);
    }
  };

  const handleClear = () => {
    setInputValue('');
    setOpen(false);
    setActiveIndex(-1);
    inputRef.current?.focus();
  };

  return (
    <Box sx={{ position: 'relative' }}>
      <SearchWrapper>
        <SearchIconWrapper>
          <SearchIcon />
        </SearchIconWrapper>

        <StyledInput
          inputRef={inputRef}
          placeholder="Search APIs…"
          inputProps={{
            'aria-label': 'search',
            'aria-autocomplete': 'list',
            'aria-controls': showDropdown ? listId : undefined,
            'aria-activedescendant': activeIndex >= 0 ? `${listId}-item-${activeIndex}` : undefined,
            'aria-expanded': showDropdown,
            role: 'combobox',
          }}
          value={inputValue}
          onChange={(e) => {
            setInputValue(e.target.value);
            setOpen(true);
            setActiveIndex(-1);
          }}
          onFocus={() => {
            if (inputValue.trim().length >= 2) setOpen(true);
          }}
          onKeyDown={handleKeyDown}
          endAdornment={
            <>
              {isLoading && (
                <CircularProgress
                  size={16}
                  sx={{ color: 'rgba(255,255,255,0.7)', mr: 1 }}
                  aria-label="loading suggestions"
                />
              )}
              {inputValue && (
                <IconButton
                  size="small"
                  aria-label="clear search"
                  onClick={handleClear}
                  sx={{ color: 'rgba(255,255,255,0.7)', p: 0.5 }}
                >
                  <ClearIcon fontSize="small" />
                </IconButton>
              )}
            </>
          }
        />
      </SearchWrapper>

      {/* Autocomplete dropdown */}
      {showDropdown && (
        <Paper
          ref={dropdownRef}
          elevation={4}
          sx={{
            position: 'absolute',
            top: '100%',
            left: (theme) => theme.spacing(3),
            right: (theme) => theme.spacing(2),
            zIndex: (theme) => theme.zIndex.modal,
            mt: 0.5,
            overflow: 'hidden',
          }}
        >
          <List id={listId} role="listbox" aria-label="search suggestions" dense sx={{ py: 0 }}>
            {suggestions.map((item, index) => (
              <ListItemButton
                key={item.apiId}
                id={`${listId}-item-${index}`}
                role="option"
                aria-selected={activeIndex === index}
                selected={activeIndex === index}
                data-testid={`suggestion-${item.apiId}`}
                onMouseDown={(e) => {
                  // Prevent blur on input
                  e.preventDefault();
                  setInputValue(item.title);
                  setOpen(false);
                  setActiveIndex(-1);
                  router.push(`/catalog/${item.apiId}`);
                }}
                onMouseEnter={() => setActiveIndex(index)}
              >
                <ListItemIcon sx={{ minWidth: 36 }}>
                  <ApiIcon fontSize="small" color="action" />
                </ListItemIcon>
                <ListItemText
                  primary={item.title}
                  secondary={
                    <Typography component="span" variant="caption" color="text.secondary">
                      {item.description?.slice(0, 80)}
                      {(item.description?.length ?? 0) > 80 ? '…' : ''}
                    </Typography>
                  }
                  slotProps={{
                    primary: { variant: 'body2', sx: { fontWeight: 500 } },
                  }}
                />
                {item.kind && (
                  <Chip
                    label={KIND_LABEL[item.kind] ?? item.kind.toUpperCase()}
                    size="small"
                    variant="outlined"
                    sx={{ ml: 1 }}
                  />
                )}
              </ListItemButton>
            ))}
          </List>
        </Paper>
      )}
    </Box>
  );
}
