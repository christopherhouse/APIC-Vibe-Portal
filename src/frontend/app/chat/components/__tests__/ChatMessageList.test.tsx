import { render, screen } from '../../../../__tests__/test-utils';
import ChatMessageList from '../ChatMessageList';
import type { ChatMessage } from '@apic-vibe-portal/shared';

const mockPush = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}));

// Suppress scrollIntoView errors in jsdom
window.HTMLElement.prototype.scrollIntoView = jest.fn();

const MESSAGES: ChatMessage[] = [
  {
    id: 'msg-1',
    role: 'user',
    content: 'What APIs are available?',
    timestamp: '2026-04-19T00:00:00.000Z',
  },
  {
    id: 'msg-2',
    role: 'assistant',
    content: 'Here are some APIs.',
    timestamp: '2026-04-19T00:00:01.000Z',
  },
];

describe('ChatMessageList', () => {
  it('renders the message list container', () => {
    render(<ChatMessageList messages={MESSAGES} isStreaming={false} />);
    expect(screen.getByTestId('chat-message-list')).toBeInTheDocument();
  });

  it('renders all provided messages', () => {
    render(<ChatMessageList messages={MESSAGES} isStreaming={false} />);
    expect(screen.getByText('What APIs are available?')).toBeInTheDocument();
    expect(screen.getByText('Here are some APIs.')).toBeInTheDocument();
  });

  it('shows typing indicator when streaming and last message is empty assistant', () => {
    const streamingMessages: ChatMessage[] = [
      ...MESSAGES,
      {
        id: 'msg-3',
        role: 'assistant',
        content: '',
        timestamp: '2026-04-19T00:00:02.000Z',
      },
    ];
    render(<ChatMessageList messages={streamingMessages} isStreaming={true} />);
    expect(screen.getByTestId('chat-typing-indicator')).toBeInTheDocument();
  });

  it('does not show typing indicator when not streaming', () => {
    render(<ChatMessageList messages={MESSAGES} isStreaming={false} />);
    expect(screen.queryByTestId('chat-typing-indicator')).not.toBeInTheDocument();
  });

  it('renders an empty list when no messages provided', () => {
    render(<ChatMessageList messages={[]} isStreaming={false} />);
    expect(screen.getByTestId('chat-message-list')).toBeInTheDocument();
    // No message bubbles should be rendered
    expect(screen.queryByText('What APIs are available?')).not.toBeInTheDocument();
  });
});
