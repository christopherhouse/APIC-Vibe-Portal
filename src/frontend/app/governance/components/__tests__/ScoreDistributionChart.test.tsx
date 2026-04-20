import { render, screen } from '../../../../__tests__/test-utils';
import ScoreDistributionChart from '../ScoreDistributionChart';
import type { ScoreDistribution } from '@/lib/governance-api';

// Recharts uses ResizeObserver and SVG features not available in jsdom.
// We mock the chart components to test the wrapper logic.
jest.mock('recharts', () => ({
  PieChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="pie-chart">{children}</div>
  ),
  Pie: () => <div data-testid="pie" />,
  Cell: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  Legend: () => <div data-testid="legend" />,
  Tooltip: () => null,
}));

const mockDistribution: ScoreDistribution = {
  excellent: 3,
  good: 5,
  needsImprovement: 2,
  poor: 0,
};

describe('ScoreDistributionChart', () => {
  it('renders the chart container', () => {
    render(<ScoreDistributionChart distribution={mockDistribution} />);
    expect(screen.getByTestId('score-distribution-chart')).toBeInTheDocument();
  });

  it('renders the chart heading', () => {
    render(<ScoreDistributionChart distribution={mockDistribution} />);
    expect(screen.getByText('Score Distribution')).toBeInTheDocument();
  });

  it('renders the pie chart when there is data', () => {
    render(<ScoreDistributionChart distribution={mockDistribution} />);
    expect(screen.getByTestId('pie-chart')).toBeInTheDocument();
  });

  it('renders empty state when all counts are zero', () => {
    const emptyDistribution: ScoreDistribution = {
      excellent: 0,
      good: 0,
      needsImprovement: 0,
      poor: 0,
    };
    render(<ScoreDistributionChart distribution={emptyDistribution} />);
    expect(screen.getByText('No data available')).toBeInTheDocument();
    expect(screen.queryByTestId('pie-chart')).not.toBeInTheDocument();
  });
});
