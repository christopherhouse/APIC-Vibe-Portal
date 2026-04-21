import { render, screen } from '../../../../__tests__/test-utils';
import FeatureUsageChart from '../FeatureUsageChart';
import type { UserActivity } from '@/lib/analytics-api';

// Mock Recharts to avoid jsdom SVG/canvas limitations.
jest.mock('recharts', () => ({
  RadarChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="radar-chart">{children}</div>
  ),
  Radar: () => <div data-testid="radar" />,
  PolarGrid: () => null,
  PolarAngleAxis: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  Tooltip: () => null,
}));

const mockActivity: UserActivity = {
  dailyActiveUsers: [],
  weeklyActiveUsers: [],
  avgSessionDurationSeconds: 0,
  avgPagesPerSession: 0,
  returningUserRate: 0,
  featureAdoption: { catalog: 100, search: 80, chat: 50, compare: 30, governance: 20 },
};

const emptyActivity: UserActivity = {
  dailyActiveUsers: [],
  weeklyActiveUsers: [],
  avgSessionDurationSeconds: 0,
  avgPagesPerSession: 0,
  returningUserRate: 0,
  featureAdoption: { catalog: 0, search: 0, chat: 0, compare: 0, governance: 0 },
};

describe('FeatureUsageChart', () => {
  it('renders chart container', () => {
    render(<FeatureUsageChart activity={mockActivity} />);
    expect(screen.getByTestId('feature-usage-chart')).toBeInTheDocument();
  });

  it('renders the heading', () => {
    render(<FeatureUsageChart activity={mockActivity} />);
    expect(screen.getByText('Feature Adoption')).toBeInTheDocument();
  });

  it('renders radar chart when there is data', () => {
    render(<FeatureUsageChart activity={mockActivity} />);
    expect(screen.getByTestId('radar-chart')).toBeInTheDocument();
  });

  it('renders empty state when no feature data', () => {
    render(<FeatureUsageChart activity={emptyActivity} />);
    expect(screen.getByText('No feature usage data available')).toBeInTheDocument();
    expect(screen.queryByTestId('radar-chart')).not.toBeInTheDocument();
  });
});
