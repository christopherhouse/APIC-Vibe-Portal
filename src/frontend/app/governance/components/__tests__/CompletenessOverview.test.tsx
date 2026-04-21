import { render, screen } from '../../../../__tests__/test-utils';
import CompletenessOverview from '../CompletenessOverview';
import type { CompletenessOverviewData } from '@/lib/metadata-api';

const mockOverview: CompletenessOverviewData = {
  averageScore: 72.5,
  averageGrade: 'C',
  totalApis: 10,
  distribution: { A: 2, B: 3, C: 2, D: 2, F: 1 },
  dimensionAverages: [
    { key: 'basicInfo', name: 'Basic Info', weight: 0.2, averageScore: 80 },
    { key: 'versioning', name: 'Versioning', weight: 0.15, averageScore: 65 },
    { key: 'specification', name: 'Specification', weight: 0.25, averageScore: 70 },
    { key: 'documentation', name: 'Documentation', weight: 0.15, averageScore: 55 },
    { key: 'classification', name: 'Classification', weight: 0.1, averageScore: 60 },
    { key: 'security', name: 'Security', weight: 0.15, averageScore: 75 },
  ],
};

describe('CompletenessOverview', () => {
  it('renders the overview card', () => {
    render(<CompletenessOverview overview={mockOverview} />);
    expect(screen.getByTestId('completeness-overview-card')).toBeInTheDocument();
  });

  it('displays the average grade', () => {
    render(<CompletenessOverview overview={mockOverview} />);
    const gradeElements = screen.getAllByText('C');
    expect(gradeElements.length).toBeGreaterThanOrEqual(1);
    // The h3 element is the prominent average grade display
    const gradeHeading = gradeElements.find(
      (el) => el.tagName === 'DIV' && el.classList.contains('MuiTypography-h3'),
    );
    expect(gradeHeading).toBeDefined();
  });

  it('displays the average score', () => {
    render(<CompletenessOverview overview={mockOverview} />);
    expect(screen.getByText('72.5')).toBeInTheDocument();
  });

  it('displays total APIs', () => {
    render(<CompletenessOverview overview={mockOverview} />);
    expect(screen.getByText(/10 APIs/)).toBeInTheDocument();
  });

  it('displays dimension names', () => {
    render(<CompletenessOverview overview={mockOverview} />);
    expect(screen.getByText('Basic Info')).toBeInTheDocument();
    expect(screen.getByText('Versioning')).toBeInTheDocument();
  });
});
