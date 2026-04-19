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
  { title: 'No URL' },
  { title: 'Unsafe Scheme', url: 'javascript:alert(1)' },
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

  it('navigates via router for relative /catalog/ citations', async () => {
    const user = userEvent.setup();
    render(<ChatCitations citations={CITATIONS} />);

    await user.click(screen.getByTestId('citation-chip-0'));
    expect(mockPush).toHaveBeenCalledWith('/catalog/payments-api');
  });

  it('does NOT use router.push for external http/https citations', () => {
    render(<ChatCitations citations={CITATIONS} />);

    // The external chip should render as an <a> tag, not trigger router.push
    const externalChip = screen.getByTestId('citation-chip-2');
    expect(externalChip.tagName.toLowerCase()).toBe('a');
    expect(externalChip).toHaveAttribute('href', 'https://external.example.com/docs');
    expect(externalChip).toHaveAttribute('target', '_blank');
    expect(externalChip).toHaveAttribute('rel', 'noopener noreferrer');
    expect(mockPush).not.toHaveBeenCalled();
  });

  it('renders non-clickable chip when citation has no URL', () => {
    render(<ChatCitations citations={CITATIONS} />);
    const noUrlChip = screen.getByTestId('citation-chip-3');
    expect(noUrlChip).toBeInTheDocument();
    // Should not have href
    expect(noUrlChip).not.toHaveAttribute('href');
  });

  it('renders non-clickable chip for unsafe URL schemes', () => {
    render(<ChatCitations citations={CITATIONS} />);
    const unsafeChip = screen.getByTestId('citation-chip-4');
    expect(unsafeChip).toBeInTheDocument();
    expect(unsafeChip).not.toHaveAttribute('href');
  });

  it('renders non-clickable chip for protocol-relative URL spoofing (//host/catalog/id)', () => {
    const spoofCitations: Citation[] = [
      { title: 'Protocol Spoof', url: '//attacker.example.com/catalog/foo' },
    ];
    render(<ChatCitations citations={spoofCitations} />);
    const chip = screen.getByTestId('citation-chip-0');
    // Should NOT be treated as a catalog link or rendered as an <a> with router navigation
    expect(chip).not.toHaveAttribute('href', '/catalog/foo');
    // Should be rendered as an external <a> (isSafeExternalUrl returns false for //-URLs)
    expect(chip).not.toHaveAttribute('href');
  });

  it('does not navigate to absolute URLs that contain /catalog/ (spoofing prevention)', () => {
    const spoofCitations: Citation[] = [
      { title: 'Spoof', url: 'https://attacker.example.com/catalog/foo' },
    ];
    render(<ChatCitations citations={spoofCitations} />);

    // Should be rendered as an external <a> (not an internal router link)
    const chip = screen.getByTestId('citation-chip-0');
    expect(chip.tagName.toLowerCase()).toBe('a');
    expect(chip).toHaveAttribute('href', 'https://attacker.example.com/catalog/foo');
    expect(mockPush).not.toHaveBeenCalled();
  });
});
