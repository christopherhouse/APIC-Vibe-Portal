import { render, screen } from '../../../../__tests__/test-utils';
import GovernanceOverview from '../GovernanceOverview';
import type { GovernanceSummary } from '@/lib/governance-api';

const mockSummary: GovernanceSummary = {
  overallScore: 78.5,
  compliantCount: 8,
  totalCount: 10,
  criticalIssues: 2,
  improvement: 1.5,
};

describe('GovernanceOverview', () => {
  it('renders all KPI cards', () => {
    render(<GovernanceOverview summary={mockSummary} />);
    expect(screen.getByTestId('overall-score-card')).toBeInTheDocument();
    expect(screen.getByTestId('compliant-apis-card')).toBeInTheDocument();
    expect(screen.getByTestId('critical-issues-card')).toBeInTheDocument();
    expect(screen.getByTestId('total-apis-card')).toBeInTheDocument();
  });

  it('displays overall score', () => {
    render(<GovernanceOverview summary={mockSummary} />);
    expect(screen.getByText('78.5')).toBeInTheDocument();
  });

  it('displays compliant count', () => {
    render(<GovernanceOverview summary={mockSummary} />);
    expect(screen.getByText('8')).toBeInTheDocument();
  });

  it('displays critical issues', () => {
    render(<GovernanceOverview summary={mockSummary} />);
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('displays total API count', () => {
    render(<GovernanceOverview summary={mockSummary} />);
    expect(screen.getByText('10')).toBeInTheDocument();
  });

  it('displays compliance percentage', () => {
    render(<GovernanceOverview summary={mockSummary} />);
    // 8/10 = 80%
    expect(screen.getByText(/80%.*10 APIs/)).toBeInTheDocument();
  });

  it('displays positive improvement trend', () => {
    render(<GovernanceOverview summary={mockSummary} />);
    expect(screen.getByText(/\+1\.5.*over last 30 days/)).toBeInTheDocument();
  });

  it('displays zero improvement correctly', () => {
    const flatSummary = { ...mockSummary, improvement: 0 };
    render(<GovernanceOverview summary={flatSummary} />);
    expect(screen.getByText(/0\.0 over last 30 days/)).toBeInTheDocument();
  });

  it('displays zero compliance when totalCount is 0', () => {
    const emptySummary = { ...mockSummary, totalCount: 0, compliantCount: 0 };
    render(<GovernanceOverview summary={emptySummary} />);
    expect(screen.getByText(/0%.*0 APIs/)).toBeInTheDocument();
  });
});
