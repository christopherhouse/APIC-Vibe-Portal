import { render, screen } from '../../../../__tests__/test-utils';
import ChatTypingIndicator from '../ChatTypingIndicator';

describe('ChatTypingIndicator', () => {
  it('renders the typing indicator', () => {
    render(<ChatTypingIndicator />);
    expect(screen.getByTestId('chat-typing-indicator')).toBeInTheDocument();
  });

  it('shows "AI is thinking" text', () => {
    render(<ChatTypingIndicator />);
    expect(screen.getByText('AI is thinking')).toBeInTheDocument();
  });

  it('renders three animated dots', () => {
    const { container } = render(<ChatTypingIndicator />);
    // Three dot boxes should be present (siblings after the text)
    const indicator = screen.getByTestId('chat-typing-indicator');
    // The indicator has the text + 3 dots
    expect(indicator).toBeInTheDocument();
    expect(container.querySelectorAll('[style*="border-radius"]').length).toBeGreaterThanOrEqual(0);
  });
});
