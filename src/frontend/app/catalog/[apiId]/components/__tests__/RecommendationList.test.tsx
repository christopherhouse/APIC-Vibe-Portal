import { render, screen } from '../../../../../__tests__/test-utils';
import RecommendationList from '../RecommendationList';
import type { Recommendation } from '@/lib/metadata-api';

const mockRecs: Recommendation[] = [
  {
    id: 'rec-1',
    dimension: 'basicInfo',
    title: 'Add description',
    description: 'Helps discoverability.',
    example: 'Example description',
    impact: 3,
    effort: 'low',
    priority: 1,
  },
  {
    id: 'rec-2',
    dimension: 'versioning',
    title: 'Create a version',
    description: 'Enables evolution.',
    example: 'v1.0.0',
    impact: 2,
    effort: 'medium',
    priority: 2,
  },
];

describe('RecommendationList', () => {
  it('renders the list', () => {
    render(<RecommendationList recommendations={mockRecs} />);
    expect(screen.getByTestId('recommendations-list')).toBeInTheDocument();
  });

  it('displays count in heading', () => {
    render(<RecommendationList recommendations={mockRecs} />);
    expect(screen.getByText('Recommendations (2)')).toBeInTheDocument();
  });

  it('renders each recommendation card', () => {
    render(<RecommendationList recommendations={mockRecs} />);
    expect(screen.getByTestId('recommendation-card-rec-1')).toBeInTheDocument();
    expect(screen.getByTestId('recommendation-card-rec-2')).toBeInTheDocument();
  });

  it('shows empty state when no recommendations', () => {
    render(<RecommendationList recommendations={[]} />);
    expect(screen.getByTestId('recommendations-list-empty')).toBeInTheDocument();
    expect(screen.getByText(/Great job/)).toBeInTheDocument();
  });
});
