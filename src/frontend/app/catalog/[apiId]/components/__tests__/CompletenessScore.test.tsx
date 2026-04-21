import { render, screen } from '../../../../../__tests__/test-utils';
import CompletenessScore from '../CompletenessScore';
import type { CompletenessScoreData } from '@/lib/metadata-api';

const mockScore: CompletenessScoreData = {
  apiId: 'test-api',
  apiName: 'Test API',
  overallScore: 78.5,
  grade: 'B',
  dimensions: [],
  lastChecked: '2024-06-01T00:00:00Z',
};

describe('CompletenessScore', () => {
  it('renders the score card', () => {
    render(<CompletenessScore score={mockScore} />);
    expect(screen.getByTestId('completeness-score-card')).toBeInTheDocument();
  });

  it('displays the grade', () => {
    render(<CompletenessScore score={mockScore} />);
    expect(screen.getByText('B')).toBeInTheDocument();
  });

  it('displays the overall score', () => {
    render(<CompletenessScore score={mockScore} />);
    expect(screen.getByText('78.5')).toBeInTheDocument();
  });

  it('displays "out of 100"', () => {
    render(<CompletenessScore score={mockScore} />);
    expect(screen.getByText('out of 100')).toBeInTheDocument();
  });

  it('renders progress indicator', () => {
    render(<CompletenessScore score={mockScore} />);
    expect(screen.getByTestId('score-progress')).toBeInTheDocument();
  });

  it('handles grade A', () => {
    const aScore = { ...mockScore, grade: 'A', overallScore: 95 };
    render(<CompletenessScore score={aScore} />);
    expect(screen.getByText('A')).toBeInTheDocument();
  });

  it('handles grade F', () => {
    const fScore = { ...mockScore, grade: 'F', overallScore: 20 };
    render(<CompletenessScore score={fScore} />);
    expect(screen.getByText('F')).toBeInTheDocument();
  });
});
