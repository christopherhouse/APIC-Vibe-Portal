import { render, screen } from '../../../../__tests__/test-utils';
import userEvent from '@testing-library/user-event';
import ChatContainer from '../ChatContainer';
import type { ChatContextValue } from '@/lib/chat-context';

const mockPush = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}));

window.HTMLElement.prototype.scrollIntoView = jest.fn();

// Mock the chat context
const mockSendMessage = jest.fn();
const mockContext: ChatContextValue = {
  sessionId: null,
  messages: [],
  isStreaming: false,
  error: null,
  isPanelOpen: false,
  sendMessage: mockSendMessage,
  newConversation: jest.fn(),
  setPanelOpen: jest.fn(),
};

jest.mock('@/lib/chat-context', () => ({
  useChatContext: () => mockContext,
  ChatProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

describe('ChatContainer', () => {
  beforeEach(() => {
    mockSendMessage.mockClear();
    mockContext.messages = [];
    mockContext.isStreaming = false;
    mockContext.error = null;
  });

  it('renders the container', () => {
    render(<ChatContainer />);
    expect(screen.getByTestId('chat-container')).toBeInTheDocument();
  });

  it('shows suggested prompts when conversation is empty', () => {
    render(<ChatContainer />);
    expect(screen.getByTestId('chat-suggestions')).toBeInTheDocument();
  });

  it('hides suggestions when there are messages', () => {
    mockContext.messages = [
      {
        id: 'msg-1',
        role: 'user',
        content: 'Hello',
        timestamp: '2026-04-19T00:00:00.000Z',
      },
    ];
    render(<ChatContainer />);
    expect(screen.queryByTestId('chat-suggestions')).not.toBeInTheDocument();
    expect(screen.getByTestId('chat-message-list')).toBeInTheDocument();
  });

  it('calls sendMessage when a suggestion is selected', async () => {
    const user = userEvent.setup();
    render(<ChatContainer />);

    await user.click(screen.getByText('Show me APIs in production'));
    expect(mockSendMessage).toHaveBeenCalledWith('Show me APIs in production');
  });

  it('shows error alert when error is present', () => {
    mockContext.error = 'Network error';
    render(<ChatContainer />);
    expect(screen.getByText('Network error')).toBeInTheDocument();
  });

  it('renders the chat input', () => {
    render(<ChatContainer />);
    expect(screen.getByTestId('chat-input')).toBeInTheDocument();
  });

  it('disables input while streaming', () => {
    mockContext.isStreaming = true;
    render(<ChatContainer />);
    expect(screen.getByTestId('chat-input')).toBeDisabled();
  });
});
