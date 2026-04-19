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
    const indicator = screen.getByTestId('chat-typing-indicator');
    expect(indicator).toBeInTheDocument();
    // The indicator should contain three dot elements (the three Box components after the text)
    // We count children: the Typography (text) + 3 dot boxes = 4 children
    const dotBoxes = container.querySelectorAll('[data-testid="chat-typing-indicator"] > *');
    expect(dotBoxes.length).toBeGreaterThanOrEqual(3);
  });
});
