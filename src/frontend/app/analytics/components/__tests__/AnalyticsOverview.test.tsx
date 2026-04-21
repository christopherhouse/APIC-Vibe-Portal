import { render, screen } from '../../../../__tests__/test-utils';
import AnalyticsOverview from '../AnalyticsOverview';
import type { AnalyticsSummary } from '@/lib/analytics-api';

const mockSummary: AnalyticsSummary = {
  totalUsers: 1234,
  totalPageViews: 5678,
  totalSearchQueries: 910,
  totalChatInteractions: 234,
  avgSessionDurationSeconds: 185,
  usersTrend: 12.5,
  pageViewsTrend: -3.2,
  searchQueriesTrend: 0,
  chatInteractionsTrend: 20.1,
};

describe('AnalyticsOverview', () => {
  it('renders all KPI cards', () => {
    render(<AnalyticsOverview summary={mockSummary} />);
    expect(screen.getByTestId('total-users-card')).toBeInTheDocument();
    expect(screen.getByTestId('page-views-card')).toBeInTheDocument();
    expect(screen.getByTestId('search-queries-card')).toBeInTheDocument();
    expect(screen.getByTestId('chat-interactions-card')).toBeInTheDocument();
    expect(screen.getByTestId('avg-session-card')).toBeInTheDocument();
  });

  it('displays total users', () => {
    render(<AnalyticsOverview summary={mockSummary} />);
    expect(screen.getByText('1,234')).toBeInTheDocument();
  });

  it('displays total page views', () => {
    render(<AnalyticsOverview summary={mockSummary} />);
    expect(screen.getByText('5,678')).toBeInTheDocument();
  });

  it('displays total search queries', () => {
    render(<AnalyticsOverview summary={mockSummary} />);
    expect(screen.getByText('910')).toBeInTheDocument();
  });

  it('displays total chat interactions', () => {
    render(<AnalyticsOverview summary={mockSummary} />);
    expect(screen.getByText('234')).toBeInTheDocument();
  });

  it('displays average session duration in minutes and seconds', () => {
    render(<AnalyticsOverview summary={mockSummary} />);
    // 185 seconds = 3m 5s
    expect(screen.getByText('3m 5s')).toBeInTheDocument();
  });

  it('displays session duration in seconds for short sessions', () => {
    render(<AnalyticsOverview summary={{ ...mockSummary, avgSessionDurationSeconds: 45 }} />);
    expect(screen.getByText('45s')).toBeInTheDocument();
  });

  it('shows positive trend for users', () => {
    render(<AnalyticsOverview summary={mockSummary} />);
    expect(screen.getByText('+12.5% vs previous period')).toBeInTheDocument();
  });

  it('shows negative trend for page views', () => {
    render(<AnalyticsOverview summary={mockSummary} />);
    expect(screen.getByText('-3.2% vs previous period')).toBeInTheDocument();
  });
});
