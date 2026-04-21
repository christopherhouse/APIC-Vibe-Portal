import { render, screen } from '../../../../__tests__/test-utils';
import SearchQueryList from '../SearchQueryList';
import type { SearchTrends } from '@/lib/analytics-api';

const mockTrends: SearchTrends = {
  dailyVolume: [],
  topQueries: [
    { queryHash: 'h1', displayTerm: 'payments api', count: 45, avgResultCount: 8 },
    { queryHash: 'h2', displayTerm: 'authentication', count: 32, avgResultCount: 12 },
    { queryHash: 'h3', displayTerm: 'openapi spec', count: 20, avgResultCount: 5 },
  ],
  zeroResultQueries: [],
  clickThroughRate: 67.5,
  avgResultsPerSearch: 9.2,
  searchModeDistribution: { keyword: 30, semantic: 50, hybrid: 20 },
};

const emptyTrends: SearchTrends = {
  dailyVolume: [],
  topQueries: [],
  zeroResultQueries: [],
  clickThroughRate: 0,
  avgResultsPerSearch: 0,
  searchModeDistribution: { keyword: 0, semantic: 0, hybrid: 0 },
};

describe('SearchQueryList', () => {
  it('renders the list container', () => {
    render(<SearchQueryList trends={mockTrends} />);
    expect(screen.getByTestId('search-query-list')).toBeInTheDocument();
  });

  it('renders the heading', () => {
    render(<SearchQueryList trends={mockTrends} />);
    expect(screen.getByText('Top Search Queries')).toBeInTheDocument();
  });

  it('renders top query terms', () => {
    render(<SearchQueryList trends={mockTrends} />);
    expect(screen.getByText('payments api')).toBeInTheDocument();
    expect(screen.getByText('authentication')).toBeInTheDocument();
  });

  it('renders query count chips', () => {
    render(<SearchQueryList trends={mockTrends} />);
    expect(screen.getByText('45')).toBeInTheDocument();
    expect(screen.getByText('32')).toBeInTheDocument();
  });

  it('renders empty state when no queries', () => {
    render(<SearchQueryList trends={emptyTrends} />);
    expect(screen.getByText('No search data available')).toBeInTheDocument();
  });
});
