import { render, screen } from '../../../../__tests__/test-utils';
import UserEngagementChart from '../UserEngagementChart';
import type { UserActivity } from '@/lib/analytics-api';

// Mock Recharts to avoid jsdom SVG/canvas limitations.
jest.mock('recharts', () => ({
  AreaChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="area-chart">{children}</div>
  ),
  Area: () => <div data-testid="area" />,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
}));

const mockActivity: UserActivity = {
  dailyActiveUsers: [
    { date: '2026-03-01', count: 85 },
    { date: '2026-03-02', count: 92 },
  ],
  weeklyActiveUsers: [],
  avgSessionDurationSeconds: 240,
  avgPagesPerSession: 4.5,
  returningUserRate: 62.3,
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

describe('UserEngagementChart', () => {
  it('renders chart container', () => {
    render(<UserEngagementChart activity={mockActivity} />);
    expect(screen.getByTestId('user-engagement-chart')).toBeInTheDocument();
  });

  it('renders the heading', () => {
    render(<UserEngagementChart activity={mockActivity} />);
    expect(screen.getByText('Daily Active Users')).toBeInTheDocument();
  });

  it('renders area chart when there is data', () => {
    render(<UserEngagementChart activity={mockActivity} />);
    expect(screen.getByTestId('area-chart')).toBeInTheDocument();
  });

  it('displays average session duration', () => {
    render(<UserEngagementChart activity={mockActivity} />);
    // 240 seconds = 4 minutes
    expect(screen.getByText('4m')).toBeInTheDocument();
  });

  it('displays pages per session', () => {
    render(<UserEngagementChart activity={mockActivity} />);
    expect(screen.getByText('4.5')).toBeInTheDocument();
  });

  it('displays return rate', () => {
    render(<UserEngagementChart activity={mockActivity} />);
    expect(screen.getByText('62.3%')).toBeInTheDocument();
  });

  it('renders empty state when no data', () => {
    render(<UserEngagementChart activity={emptyActivity} />);
    expect(screen.getByText('No user data available')).toBeInTheDocument();
    expect(screen.queryByTestId('area-chart')).not.toBeInTheDocument();
  });
});
