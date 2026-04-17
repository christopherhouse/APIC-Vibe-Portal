import { render, screen } from '../../../../__tests__/test-utils';
import SearchSummary from '../SearchSummary';

describe('SearchSummary', () => {
  it('shows the result count and query', () => {
    render(<SearchSummary query="payment" totalCount={42} queryDuration={123} />);
    expect(screen.getByTestId('search-summary')).toBeInTheDocument();
    expect(screen.getByText(/42/)).toBeInTheDocument();
    expect(screen.getByText(/payment/)).toBeInTheDocument();
  });

  it('shows singular "result" for 1 result', () => {
    render(<SearchSummary query="x" totalCount={1} queryDuration={50} />);
    expect(screen.getByText(/1/)).toBeInTheDocument();
    // Should say "result" not "results"
    expect(screen.queryByText(/results/)).not.toBeInTheDocument();
  });

  it('shows No results found when count is 0', () => {
    render(<SearchSummary query="xyz" totalCount={0} queryDuration={10} />);
    expect(screen.getByText(/No results found/i)).toBeInTheDocument();
  });

  it('shows query duration', () => {
    render(<SearchSummary query="api" totalCount={5} queryDuration={88} />);
    expect(screen.getByText(/88ms/)).toBeInTheDocument();
  });
});
