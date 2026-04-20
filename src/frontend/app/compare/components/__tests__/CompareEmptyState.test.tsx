import { render, screen } from '../../../../__tests__/test-utils';
import CompareEmptyState from '../CompareEmptyState';

const mockPush = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
  useSearchParams: () => new URLSearchParams(),
}));

describe('CompareEmptyState', () => {
  beforeEach(() => {
    mockPush.mockClear();
  });

  it('renders the empty state container', () => {
    render(<CompareEmptyState />);
    expect(screen.getByTestId('compare-empty-state')).toBeInTheDocument();
  });

  it('shows the heading', () => {
    render(<CompareEmptyState />);
    expect(screen.getByText('No APIs selected for comparison')).toBeInTheDocument();
  });

  it('shows instructional text', () => {
    render(<CompareEmptyState />);
    expect(screen.getByText(/Select 2 to 5 APIs/)).toBeInTheDocument();
  });

  it('has a Browse Catalog button', () => {
    render(<CompareEmptyState />);
    expect(screen.getByRole('button', { name: 'Browse Catalog' })).toBeInTheDocument();
  });
});
