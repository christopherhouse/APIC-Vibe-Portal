import { render, screen } from '../../../../__tests__/test-utils';
import userEvent from '@testing-library/user-event';
import ChatCitations from '../ChatCitations';
import type { Citation } from '@apic-vibe-portal/shared';

const mockPush = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}));

const CITATIONS: Citation[] = [
  { title: 'Payments API', url: '/catalog/payments-api', content: 'A payment processing API' },
  { title: 'Auth API', url: '/catalog/auth-api' },
  { title: 'External Source', url: 'https://external.example.com/docs' },
];

describe('ChatCitations', () => {
  beforeEach(() => mockPush.mockClear());

  it('renders nothing when citations array is empty', () => {
    const { container } = render(<ChatCitations citations={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders citation chips', () => {
    render(<ChatCitations citations={CITATIONS} />);
    expect(screen.getByTestId('citation-chip-0')).toBeInTheDocument();
    expect(screen.getByTestId('citation-chip-1')).toBeInTheDocument();
    expect(screen.getByTestId('citation-chip-2')).toBeInTheDocument();
  });

  it('displays citation titles', () => {
    render(<ChatCitations citations={CITATIONS} />);
    expect(screen.getByText('Payments API')).toBeInTheDocument();
    expect(screen.getByText('Auth API')).toBeInTheDocument();
  });

  it('navigates to catalog page when clicking a catalog citation', async () => {
    const user = userEvent.setup();
    render(<ChatCitations citations={CITATIONS} />);

    await user.click(screen.getByTestId('citation-chip-0'));
    expect(mockPush).toHaveBeenCalledWith('/catalog/payments-api');
  });

  it('navigates to external URL for non-catalog citations', async () => {
    const user = userEvent.setup();
    render(<ChatCitations citations={CITATIONS} />);

    await user.click(screen.getByTestId('citation-chip-2'));
    expect(mockPush).toHaveBeenCalledWith('https://external.example.com/docs');
  });
});
