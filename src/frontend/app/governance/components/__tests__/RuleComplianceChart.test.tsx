import { render, screen } from '../../../../__tests__/test-utils';
import RuleComplianceChart from '../RuleComplianceChart';
import type { RuleCompliance } from '@/lib/governance-api';

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
  Cell: () => null,
}));

const mockCompliance: RuleCompliance[] = [
  {
    ruleId: 'metadata.description',
    ruleName: 'API Description Required',
    severity: 'warning',
    passCount: 8,
    failCount: 2,
    complianceRate: 80.0,
  },
  {
    ruleId: 'versioning.has-version',
    ruleName: 'API Must Have Version',
    severity: 'critical',
    passCount: 10,
    failCount: 0,
    complianceRate: 100.0,
  },
];

describe('RuleComplianceChart', () => {
  it('renders the chart container', () => {
    render(<RuleComplianceChart compliance={mockCompliance} />);
    expect(screen.getByTestId('rule-compliance-chart')).toBeInTheDocument();
  });

  it('renders the chart heading', () => {
    render(<RuleComplianceChart compliance={mockCompliance} />);
    expect(screen.getByText('Rule Compliance Rates')).toBeInTheDocument();
  });

  it('renders the bar chart when there is data', () => {
    render(<RuleComplianceChart compliance={mockCompliance} />);
    expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
  });

  it('renders empty state when no compliance data', () => {
    render(<RuleComplianceChart compliance={[]} />);
    expect(screen.getByText('No data available')).toBeInTheDocument();
    expect(screen.queryByTestId('bar-chart')).not.toBeInTheDocument();
  });

  it('shows subtitle about top 10 rules', () => {
    render(<RuleComplianceChart compliance={mockCompliance} />);
    expect(screen.getByText('Showing top 10 rules with lowest compliance')).toBeInTheDocument();
  });
});
