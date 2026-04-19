import { render, screen } from '../../../../__tests__/test-utils';
import userEvent from '@testing-library/user-event';
import ChatSidePanel from '../ChatSidePanel';
import type { ChatContextValue } from '@/lib/chat-context';

const mockPush = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}));

window.HTMLElement.prototype.scrollIntoView = jest.fn();

const mockSetPanelOpen = jest.fn();
const mockNewConversation = jest.fn();

const mockContext: ChatContextValue = {
  sessionId: null,
  messages: [],
  isStreaming: false,
  error: null,
  isPanelOpen: false,
  sendMessage: jest.fn(),
  newConversation: mockNewConversation,
  setPanelOpen: mockSetPanelOpen,
};

jest.mock('@/lib/chat-context', () => ({
  useChatContext: () => mockContext,
  ChatProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

describe('ChatSidePanel', () => {
  beforeEach(() => {
    mockSetPanelOpen.mockClear();
    mockNewConversation.mockClear();
    mockContext.isPanelOpen = false;
    mockContext.messages = [];
  });

  it('renders the floating action button', () => {
    render(<ChatSidePanel />);
    expect(screen.getByTestId('chat-fab')).toBeInTheDocument();
  });

  it('opens the panel when FAB is clicked', async () => {
    const user = userEvent.setup();
    render(<ChatSidePanel />);

    await user.click(screen.getByTestId('chat-fab'));
    expect(mockSetPanelOpen).toHaveBeenCalledWith(true);
  });

  it('closes the panel when FAB is clicked while open', async () => {
    const user = userEvent.setup();
    mockContext.isPanelOpen = true;
    render(<ChatSidePanel />);

    await user.click(screen.getByTestId('chat-fab'));
    expect(mockSetPanelOpen).toHaveBeenCalledWith(false);
  });

  it('shows new conversation button when there are messages', () => {
    mockContext.isPanelOpen = true;
    mockContext.messages = [
      { id: 'msg-1', role: 'user', content: 'Hello', timestamp: '2026-04-19T00:00:00.000Z' },
    ];
    render(<ChatSidePanel />);
    expect(screen.getByTestId('new-conversation-button')).toBeInTheDocument();
  });

  it('hides new conversation button when conversation is empty', () => {
    mockContext.isPanelOpen = true;
    mockContext.messages = [];
    render(<ChatSidePanel />);
    expect(screen.queryByTestId('new-conversation-button')).not.toBeInTheDocument();
  });

  it('calls newConversation when new conversation button is clicked', async () => {
    const user = userEvent.setup();
    mockContext.isPanelOpen = true;
    mockContext.messages = [
      { id: 'msg-1', role: 'user', content: 'Hello', timestamp: '2026-04-19T00:00:00.000Z' },
    ];
    render(<ChatSidePanel />);

    await user.click(screen.getByTestId('new-conversation-button'));
    expect(mockNewConversation).toHaveBeenCalled();
  });
});
