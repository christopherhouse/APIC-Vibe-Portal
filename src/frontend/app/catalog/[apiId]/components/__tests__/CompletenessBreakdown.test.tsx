import { render, screen } from '../../../../../__tests__/test-utils';
import CompletenessBreakdown from '../CompletenessBreakdown';
import type { DimensionScore } from '@/lib/metadata-api';

const mockDimensions: DimensionScore[] = [
  { key: 'basicInfo', name: 'Basic Info', weight: 0.2, score: 80 },
  { key: 'versioning', name: 'Versioning', weight: 0.15, score: 60 },
  { key: 'specification', name: 'Specification', weight: 0.25, score: 40 },
  { key: 'documentation', name: 'Documentation', weight: 0.15, score: 100 },
  { key: 'classification', name: 'Classification', weight: 0.1, score: 50 },
  { key: 'security', name: 'Security', weight: 0.15, score: 30 },
];

describe('CompletenessBreakdown', () => {
  it('renders the breakdown card', () => {
    render(<CompletenessBreakdown dimensions={mockDimensions} />);
    expect(screen.getByTestId('completeness-breakdown-card')).toBeInTheDocument();
  });

  it('renders all dimension names', () => {
    render(<CompletenessBreakdown dimensions={mockDimensions} />);
    expect(screen.getByText('Basic Info')).toBeInTheDocument();
    expect(screen.getByText('Versioning')).toBeInTheDocument();
    expect(screen.getByText('Specification')).toBeInTheDocument();
    expect(screen.getByText('Documentation')).toBeInTheDocument();
    expect(screen.getByText('Classification')).toBeInTheDocument();
    expect(screen.getByText('Security')).toBeInTheDocument();
  });

  it('renders dimension test IDs', () => {
    render(<CompletenessBreakdown dimensions={mockDimensions} />);
    expect(screen.getByTestId('dimension-basicInfo')).toBeInTheDocument();
    expect(screen.getByTestId('dimension-versioning')).toBeInTheDocument();
  });

  it('renders progress bars for each dimension', () => {
    render(<CompletenessBreakdown dimensions={mockDimensions} />);
    expect(screen.getByTestId('dimension-progress-basicInfo')).toBeInTheDocument();
    expect(screen.getByTestId('dimension-progress-security')).toBeInTheDocument();
  });

  it('renders empty list gracefully', () => {
    render(<CompletenessBreakdown dimensions={[]} />);
    expect(screen.getByTestId('completeness-breakdown-card')).toBeInTheDocument();
  });
});
