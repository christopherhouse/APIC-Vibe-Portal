import { render, screen } from '../../../../__tests__/test-utils';
import SearchEffectivenessChart from '../SearchEffectivenessChart';
import type { SearchTrends } from '@/lib/analytics-api';

// Mock Recharts to avoid jsdom SVG/canvas limitations.
jest.mock('recharts', () => ({
  BarChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="bar-chart">{children}</div>
  ),
  Bar: () => <div data-testid="bar" />,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
}));

const mockTrends: SearchTrends = {
  dailyVolume: [
    { date: '2026-03-01', queryCount: 120, zeroResultCount: 10 },
    { date: '2026-03-02', queryCount: 145, zeroResultCount: 8 },
  ],
  topQueries: [],
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

describe('SearchEffectivenessChart', () => {
  it('renders chart container', () => {
    render(<SearchEffectivenessChart trends={mockTrends} />);
    expect(screen.getByTestId('search-effectiveness-chart')).toBeInTheDocument();
  });

  it('renders the heading', () => {
    render(<SearchEffectivenessChart trends={mockTrends} />);
    expect(screen.getByText('Search Volume & Zero Results')).toBeInTheDocument();
  });

  it('displays click-through rate', () => {
    render(<SearchEffectivenessChart trends={mockTrends} />);
    expect(screen.getByText('67.5%')).toBeInTheDocument();
  });

  it('displays average results per search', () => {
    render(<SearchEffectivenessChart trends={mockTrends} />);
    expect(screen.getByText('9.2')).toBeInTheDocument();
  });

  it('renders bar chart when there is data', () => {
    render(<SearchEffectivenessChart trends={mockTrends} />);
    expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
  });

  it('renders empty state when no data', () => {
    render(<SearchEffectivenessChart trends={emptyTrends} />);
    expect(screen.getByText('No search data available')).toBeInTheDocument();
    expect(screen.queryByTestId('bar-chart')).not.toBeInTheDocument();
  });
});
