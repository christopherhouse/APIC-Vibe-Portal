import { render, screen } from '../../../../__tests__/test-utils';
import NoResults from '../NoResults';

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

describe('NoResults', () => {
  it('shows a message with the search query', () => {
    render(<NoResults query="payment api" />);
    expect(screen.getByTestId('no-results')).toBeInTheDocument();
    expect(screen.getByText(/No APIs found/)).toBeInTheDocument();
    expect(screen.getByText(/payment api/)).toBeInTheDocument();
  });

  it('shows fallback message when query is empty', () => {
    render(<NoResults query="" />);
    expect(screen.getByText(/No APIs found/)).toBeInTheDocument();
  });

  it('renders Browse catalog link', () => {
    render(<NoResults query="foo" />);
    expect(screen.getByRole('link', { name: /browse catalog/i })).toBeInTheDocument();
  });

  it('shows helpful suggestions text', () => {
    render(<NoResults query="foo" />);
    expect(screen.getByText(/Try different keywords/i)).toBeInTheDocument();
  });
});
