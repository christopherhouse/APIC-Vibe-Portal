import { render, screen } from '../../../../__tests__/test-utils';
import UsageTrendChart from '../UsageTrendChart';
import type { UsageTrends } from '@/lib/analytics-api';

// Mock Recharts to avoid jsdom SVG/canvas limitations.
jest.mock('recharts', () => ({
  LineChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="line-chart">{children}</div>
  ),
  Line: () => <div data-testid="line" />,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
}));

const mockTrends: UsageTrends = {
  range: '30d',
  dataPoints: [
    {
      date: '2026-03-01',
      activeUsers: 120,
      pageViews: 450,
      searches: 80,
      chatInteractions: 30,
    },
    {
      date: '2026-03-02',
      activeUsers: 135,
      pageViews: 500,
      searches: 95,
      chatInteractions: 42,
    },
  ],
};

const emptyTrends: UsageTrends = {
  range: '30d',
  dataPoints: [],
};

describe('UsageTrendChart', () => {
  it('renders chart container', () => {
    render(<UsageTrendChart trends={mockTrends} />);
    expect(screen.getByTestId('usage-trend-chart')).toBeInTheDocument();
  });

  it('renders the chart heading', () => {
    render(<UsageTrendChart trends={mockTrends} />);
    expect(screen.getByText('Usage Trends')).toBeInTheDocument();
  });

  it('renders a line chart when there is data', () => {
    render(<UsageTrendChart trends={mockTrends} />);
    expect(screen.getByTestId('line-chart')).toBeInTheDocument();
  });

  it('renders empty state when there is no data', () => {
    render(<UsageTrendChart trends={emptyTrends} />);
    expect(screen.getByText('No data available')).toBeInTheDocument();
    expect(screen.queryByTestId('line-chart')).not.toBeInTheDocument();
  });
});
