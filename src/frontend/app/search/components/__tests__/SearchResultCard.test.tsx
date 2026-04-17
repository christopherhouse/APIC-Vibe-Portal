import { render, screen } from '../../../../__tests__/test-utils';
import userEvent from '@testing-library/user-event';
import SearchResultCard from '../SearchResultCard';
import { ApiKind, ApiLifecycle } from '@apic-vibe-portal/shared';
import type { SearchResultItem } from '@/lib/search-api';

const mockPush = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}));

const mockResult: SearchResultItem = {
  apiId: 'api-1',
  apiName: 'petstore',
  title: 'Petstore API',
  description: 'A sample API for managing pets.',
  kind: ApiKind.REST,
  lifecycleStage: ApiLifecycle.Production,
  score: 0.85,
};

describe('SearchResultCard', () => {
  beforeEach(() => mockPush.mockClear());

  it('renders title and description', () => {
    render(<SearchResultCard result={mockResult} />);
    expect(screen.getByText('Petstore API')).toBeInTheDocument();
    expect(screen.getByText(/A sample API/)).toBeInTheDocument();
  });

  it('renders kind and lifecycle badges', () => {
    render(<SearchResultCard result={mockResult} />);
    expect(screen.getByText('REST')).toBeInTheDocument();
    expect(screen.getByText('Production')).toBeInTheDocument();
  });

  it('navigates to catalog detail on click', async () => {
    const user = userEvent.setup();
    render(<SearchResultCard result={mockResult} />);
    // Click inside the CardActionArea (on the title text)
    await user.click(screen.getByText('Petstore API'));
    expect(mockPush).toHaveBeenCalledWith('/catalog/api-1');
  });

  it('renders semantic caption when present', () => {
    const withCaption: SearchResultItem = {
      ...mockResult,
      semanticCaption: 'An AI-generated description of this API.',
    };
    render(<SearchResultCard result={withCaption} />);
    expect(screen.getByTestId('semantic-caption')).toBeInTheDocument();
    expect(screen.getByText('An AI-generated description of this API.')).toBeInTheDocument();
  });

  it('does not render semantic caption when absent', () => {
    render(<SearchResultCard result={mockResult} />);
    expect(screen.queryByTestId('semantic-caption')).not.toBeInTheDocument();
  });

  it('renders highlighted text when highlights are provided', () => {
    const withHighlights: SearchResultItem = {
      ...mockResult,
      highlights: {
        title: ['<em>Petstore</em> API'],
        description: ['A sample API for managing <em>pets</em>.'],
      },
    };
    render(<SearchResultCard result={withHighlights} />);
    // highlighted-text nodes should be present
    const highlighted = screen.getAllByTestId('highlighted-text');
    expect(highlighted.length).toBeGreaterThan(0);
  });

  it('shows a relevance progress bar', () => {
    render(<SearchResultCard result={mockResult} />);
    expect(screen.getByRole('progressbar', { name: /relevance/i })).toBeInTheDocument();
  });
});
