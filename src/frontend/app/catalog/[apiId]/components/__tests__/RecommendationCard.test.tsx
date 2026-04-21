import { render, screen } from '../../../../../__tests__/test-utils';
import RecommendationCard from '../RecommendationCard';
import type { Recommendation } from '@/lib/metadata-api';

const mockRec: Recommendation = {
  id: 'basic-info-description',
  dimension: 'basicInfo',
  title: 'Add a detailed API description',
  description: 'A thorough description helps developers.',
  example: 'The Petstore API provides endpoints...',
  impact: 3,
  effort: 'low',
  priority: 1,
};

describe('RecommendationCard', () => {
  it('renders the card', () => {
    render(<RecommendationCard recommendation={mockRec} />);
    expect(screen.getByTestId('recommendation-card-basic-info-description')).toBeInTheDocument();
  });

  it('displays the title with priority', () => {
    render(<RecommendationCard recommendation={mockRec} />);
    expect(screen.getByText('#1 — Add a detailed API description')).toBeInTheDocument();
  });

  it('displays the description', () => {
    render(<RecommendationCard recommendation={mockRec} />);
    expect(screen.getByText('A thorough description helps developers.')).toBeInTheDocument();
  });

  it('displays the example', () => {
    render(<RecommendationCard recommendation={mockRec} />);
    expect(screen.getByText('The Petstore API provides endpoints...')).toBeInTheDocument();
  });

  it('displays the impact chip', () => {
    render(<RecommendationCard recommendation={mockRec} />);
    expect(screen.getByTestId('impact-chip')).toBeInTheDocument();
    expect(screen.getByText('High Impact')).toBeInTheDocument();
  });

  it('displays the effort chip', () => {
    render(<RecommendationCard recommendation={mockRec} />);
    expect(screen.getByTestId('effort-chip')).toBeInTheDocument();
    expect(screen.getByText('low effort')).toBeInTheDocument();
  });
});
