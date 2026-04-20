'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import Tooltip from '@mui/material/Tooltip';
import IconButton from '@mui/material/IconButton';
import Button from '@mui/material/Button';
import CompareArrowsIcon from '@mui/icons-material/CompareArrows';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';

const MAX_COMPARE = 5;

/** Adds or removes an API ID from the `compare` URL query parameter. */
function toggleCompareId(searchParams: URLSearchParams, apiId: string): string {
  const current = (searchParams.get('compare') ?? '').split(',').filter(Boolean);
  const isSelected = current.includes(apiId);
  const updated = isSelected ? current.filter((id) => id !== apiId) : [...current, apiId];
  const next = new URLSearchParams(searchParams.toString());
  if (updated.length === 0) {
    next.delete('compare');
  } else {
    next.set('compare', updated.join(','));
  }
  return next.toString();
}

export interface CompareAddButtonProps {
  apiId: string;
  /** Visual variant — 'icon' for compact placement on cards, 'button' for detail pages. */
  variant?: 'icon' | 'button';
}

export default function CompareAddButton({ apiId, variant = 'icon' }: CompareAddButtonProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const current = (searchParams.get('compare') ?? '').split(',').filter(Boolean);
  const isSelected = current.includes(apiId);
  const isFull = current.length >= MAX_COMPARE && !isSelected;

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    const next = toggleCompareId(new URLSearchParams(searchParams.toString()), apiId);
    const url = next ? `?${next}` : window.location.pathname;
    router.push(url, { scroll: false });
  };

  const label = isSelected ? 'Remove from comparison' : isFull ? 'Max 5 APIs' : 'Add to compare';

  if (variant === 'button') {
    return (
      <Button
        variant={isSelected ? 'contained' : 'outlined'}
        size="small"
        startIcon={isSelected ? <CheckCircleIcon /> : <CompareArrowsIcon />}
        onClick={handleClick}
        disabled={isFull}
        color={isSelected ? 'success' : 'primary'}
        data-testid={`compare-add-button-${apiId}`}
      >
        {isSelected ? 'Added to Compare' : 'Add to Compare'}
      </Button>
    );
  }

  return (
    <Tooltip title={label}>
      <span>
        <IconButton
          size="small"
          onClick={handleClick}
          disabled={isFull}
          color={isSelected ? 'success' : 'default'}
          aria-label={label}
          data-testid={`compare-add-button-${apiId}`}
        >
          {isSelected ? (
            <CheckCircleIcon fontSize="small" />
          ) : (
            <CompareArrowsIcon fontSize="small" />
          )}
        </IconButton>
      </span>
    </Tooltip>
  );
}
