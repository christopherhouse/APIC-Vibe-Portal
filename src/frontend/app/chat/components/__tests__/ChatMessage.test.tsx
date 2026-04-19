import { render, screen } from '../../../../__tests__/test-utils';
import ChatMessageBubble from '../ChatMessage';
import type { ChatMessage } from '@apic-vibe-portal/shared';

// Mock clipboard
Object.assign(navigator, {
  clipboard: { writeText: jest.fn().mockResolvedValue(undefined) },
});

const mockPush = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}));

const USER_MSG: ChatMessage = {
  id: 'msg-1',
  role: 'user',
  content: 'Hello, what APIs are available?',
  timestamp: '2026-04-19T00:00:00.000Z',
};

const ASSISTANT_MSG: ChatMessage = {
  id: 'msg-2',
  role: 'assistant',
  content: 'Here are some **available** APIs:\n- Payments\n- Auth',
  timestamp: '2026-04-19T00:00:01.000Z',
};

const ASSISTANT_WITH_CITATIONS: ChatMessage = {
  id: 'msg-3',
  role: 'assistant',
  content: 'The Payments API supports credit cards.',
  citations: [{ title: 'Payments API', url: '/catalog/payments-api' }],
  timestamp: '2026-04-19T00:00:02.000Z',
};

describe('ChatMessageBubble', () => {
  it('renders user message content', () => {
    render(<ChatMessageBubble message={USER_MSG} />);
    expect(screen.getByText('Hello, what APIs are available?')).toBeInTheDocument();
  });

  it('renders assistant message with data-testid', () => {
    render(<ChatMessageBubble message={ASSISTANT_MSG} />);
    expect(screen.getByTestId('chat-message-msg-2')).toBeInTheDocument();
  });

  it('renders assistant message markdown content', () => {
    render(<ChatMessageBubble message={ASSISTANT_MSG} />);
    // The mock renders markdown as plain text inside a div
    expect(screen.getByTestId('markdown-content')).toBeInTheDocument();
    // The raw content should be visible
    expect(screen.getByTestId('markdown-content')).toHaveTextContent('available');
  });

  it('shows copy button for assistant messages', () => {
    render(<ChatMessageBubble message={ASSISTANT_MSG} />);
    expect(screen.getByTestId('copy-button')).toBeInTheDocument();
  });

  it('does not show copy button for user messages', () => {
    render(<ChatMessageBubble message={USER_MSG} />);
    expect(screen.queryByTestId('copy-button')).not.toBeInTheDocument();
  });

  it('renders citations when present', () => {
    render(<ChatMessageBubble message={ASSISTANT_WITH_CITATIONS} />);
    expect(screen.getByText('Payments API')).toBeInTheDocument();
  });

  it('does not render citations section when citations are absent', () => {
    render(<ChatMessageBubble message={ASSISTANT_MSG} />);
    expect(screen.queryByText('Sources')).not.toBeInTheDocument();
  });
});
