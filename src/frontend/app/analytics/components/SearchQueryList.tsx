'use client';

import {
  Box,
  Card,
  CardContent,
  Chip,
  List,
  ListItem,
  ListItemText,
  Typography,
} from '@mui/material';
import type { SearchTrends } from '@/lib/analytics-api';

interface SearchQueryListProps {
  trends: SearchTrends;
}

export default function SearchQueryList({ trends }: SearchQueryListProps) {
  const topQueries = trends.topQueries.slice(0, 10);

  if (topQueries.length === 0) {
    return (
      <Card data-testid="search-query-list">
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Top Search Queries
          </Typography>
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              No search data available
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  const maxCount = topQueries[0]?.count ?? 1;

  return (
    <Card data-testid="search-query-list">
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Top Search Queries
        </Typography>
        <List dense disablePadding>
          {topQueries.map((query, index) => (
            <ListItem
              key={query.queryHash}
              data-testid={`search-query-item-${index}`}
              sx={{ px: 0, py: 0.5 }}
            >
              <ListItemText
                primary={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="body2" sx={{ flexGrow: 1 }}>
                      {query.displayTerm}
                    </Typography>
                    <Chip label={query.count} size="small" variant="outlined" />
                  </Box>
                }
                secondary={
                  <Box
                    sx={{
                      mt: 0.25,
                      height: 4,
                      borderRadius: 2,
                      bgcolor: 'primary.light',
                      width: `${Math.round((query.count / maxCount) * 100)}%`,
                      opacity: 0.6,
                    }}
                  />
                }
              />
            </ListItem>
          ))}
        </List>
      </CardContent>
    </Card>
  );
}
