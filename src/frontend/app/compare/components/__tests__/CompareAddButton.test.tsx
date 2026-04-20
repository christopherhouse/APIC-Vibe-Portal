import { render, screen } from '../../../../__tests__/test-utils';
import userEvent from '@testing-library/user-event';
import CompareAddButton from '../CompareAddButton';

const mockPush = jest.fn();
let mockSearchParams = new URLSearchParams();

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
  useSearchParams: () => mockSearchParams,
}));

describe('CompareAddButton — icon variant', () => {
  beforeEach(() => {
    mockPush.mockClear();
    mockSearchParams = new URLSearchParams();
  });

  it('renders the icon button', () => {
    render(<CompareAddButton apiId="api-1" />);
    expect(screen.getByTestId('compare-add-button-api-1')).toBeInTheDocument();
  });

  it('calls router.push when clicked', async () => {
    const user = userEvent.setup();
    render(<CompareAddButton apiId="api-1" />);
    await user.click(screen.getByTestId('compare-add-button-api-1'));
    expect(mockPush).toHaveBeenCalledWith(
      expect.stringContaining('compare=api-1'),
      expect.anything()
    );
  });

  it('shows remove icon when already selected', () => {
    mockSearchParams = new URLSearchParams('compare=api-1');
    render(<CompareAddButton apiId="api-1" />);
    const btn = screen.getByTestId('compare-add-button-api-1');
    expect(btn).toBeInTheDocument();
    // aria-label should reflect selected state
    expect(btn.closest('button')).toHaveAttribute('aria-label', 'Remove from comparison');
  });

  it('is disabled when max 5 APIs already selected', () => {
    mockSearchParams = new URLSearchParams('compare=a1,a2,a3,a4,a5');
    render(<CompareAddButton apiId="new-api" />);
    expect(screen.getByTestId('compare-add-button-new-api').closest('button')).toBeDisabled();
  });
});

describe('CompareAddButton — button variant', () => {
  beforeEach(() => {
    mockPush.mockClear();
    mockSearchParams = new URLSearchParams();
  });

  it('renders as a button with text', () => {
    render(<CompareAddButton apiId="api-1" variant="button" />);
    expect(screen.getByRole('button', { name: /Add to Compare/i })).toBeInTheDocument();
  });

  it('shows "Added to Compare" when selected', () => {
    mockSearchParams = new URLSearchParams('compare=api-1');
    render(<CompareAddButton apiId="api-1" variant="button" />);
    expect(screen.getByRole('button', { name: /Added to Compare/i })).toBeInTheDocument();
  });
});
