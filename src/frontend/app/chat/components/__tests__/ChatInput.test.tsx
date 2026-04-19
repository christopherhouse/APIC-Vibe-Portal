import { render, screen } from '../../../../__tests__/test-utils';
import userEvent from '@testing-library/user-event';
import ChatInput from '../ChatInput';

describe('ChatInput', () => {
  it('renders the text input and send button', () => {
    render(<ChatInput onSend={jest.fn()} />);
    expect(screen.getByTestId('chat-input')).toBeInTheDocument();
    expect(screen.getByTestId('send-button')).toBeInTheDocument();
  });

  it('calls onSend when the send button is clicked', async () => {
    const user = userEvent.setup();
    const onSend = jest.fn();
    render(<ChatInput onSend={onSend} />);

    const input = screen.getByTestId('chat-input');
    await user.type(input, 'Hello world');
    await user.click(screen.getByTestId('send-button'));

    expect(onSend).toHaveBeenCalledWith('Hello world');
  });

  it('calls onSend on Enter key press', async () => {
    const user = userEvent.setup();
    const onSend = jest.fn();
    render(<ChatInput onSend={onSend} />);

    const input = screen.getByTestId('chat-input');
    await user.type(input, 'Test message{Enter}');

    expect(onSend).toHaveBeenCalledWith('Test message');
  });

  it('does NOT send on Shift+Enter', async () => {
    const user = userEvent.setup();
    const onSend = jest.fn();
    render(<ChatInput onSend={onSend} />);

    const input = screen.getByTestId('chat-input');
    await user.type(input, 'Line1{Shift>}{Enter}{/Shift}Line2');
    // Should not have sent yet
    expect(onSend).not.toHaveBeenCalled();
  });

  it('disables the input and shows spinner when disabled=true', () => {
    render(<ChatInput onSend={jest.fn()} disabled />);
    const input = screen.getByTestId('chat-input');
    expect(input).toBeDisabled();
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('clears the input after sending', async () => {
    const user = userEvent.setup();
    const onSend = jest.fn();
    render(<ChatInput onSend={onSend} />);

    const input = screen.getByTestId('chat-input');
    await user.type(input, 'My message{Enter}');

    expect(input).toHaveValue('');
  });

  it('does not call onSend when input is empty', () => {
    const onSend = jest.fn();
    render(<ChatInput onSend={onSend} />);

    // The send button should be disabled (not clickable) when input is empty
    expect(screen.getByTestId('send-button')).toBeDisabled();
    expect(onSend).not.toHaveBeenCalled();
  });
});
