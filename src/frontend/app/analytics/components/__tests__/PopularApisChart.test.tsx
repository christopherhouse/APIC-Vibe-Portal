import { render, screen } from '../../../../__tests__/test-utils';
import PopularApisChart from '../PopularApisChart';
import type { PopularApi } from '@/lib/analytics-api';

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
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
}));

const mockApis: PopularApi[] = [
  {
    apiId: 'payments-api',
    apiName: 'Payments API',
    viewCount: 500,
    downloadCount: 120,
    chatMentionCount: 45,
  },
  {
    apiId: 'users-api',
    apiName: 'Users API',
    viewCount: 380,
    downloadCount: 90,
    chatMentionCount: 30,
  },
];

describe('PopularApisChart', () => {
  it('renders chart container', () => {
    render(<PopularApisChart apis={mockApis} />);
    expect(screen.getByTestId('popular-apis-chart')).toBeInTheDocument();
  });

  it('renders the chart heading', () => {
    render(<PopularApisChart apis={mockApis} />);
    expect(screen.getByText('Top APIs by Views')).toBeInTheDocument();
  });

  it('renders a bar chart when there is data', () => {
    render(<PopularApisChart apis={mockApis} />);
    expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
  });

  it('renders empty state when no APIs', () => {
    render(<PopularApisChart apis={[]} />);
    expect(screen.getByText('No data available')).toBeInTheDocument();
    expect(screen.queryByTestId('bar-chart')).not.toBeInTheDocument();
  });
});
