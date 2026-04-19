import { render, screen } from '../../../../__tests__/test-utils';
import userEvent from '@testing-library/user-event';
import ChatSuggestions from '../ChatSuggestions';

describe('ChatSuggestions', () => {
  it('renders the suggestions container', () => {
    render(<ChatSuggestions onSelect={jest.fn()} />);
    expect(screen.getByTestId('chat-suggestions')).toBeInTheDocument();
  });

  it('renders all starter prompts', () => {
    render(<ChatSuggestions onSelect={jest.fn()} />);
    const prompts = screen.getAllByTestId('suggestion-prompt');
    expect(prompts).toHaveLength(4);
  });

  it('calls onSelect with the correct prompt when clicked', async () => {
    const user = userEvent.setup();
    const onSelect = jest.fn();
    render(<ChatSuggestions onSelect={onSelect} />);

    await user.click(screen.getByText('Show me APIs in production'));
    expect(onSelect).toHaveBeenCalledWith('Show me APIs in production');
  });

  it('renders the heading text', () => {
    render(<ChatSuggestions onSelect={jest.fn()} />);
    expect(screen.getByText('How can I help you discover APIs?')).toBeInTheDocument();
  });
});
