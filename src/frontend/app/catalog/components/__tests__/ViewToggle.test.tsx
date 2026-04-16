import { render, screen } from '../../../../__tests__/test-utils';
import userEvent from '@testing-library/user-event';
import ViewToggle from '../ViewToggle';

describe('ViewToggle', () => {
  const onChange = jest.fn();

  beforeEach(() => {
    onChange.mockClear();
  });

  it('renders grid and list toggle buttons', () => {
    render(<ViewToggle viewMode="grid" onChange={onChange} />);
    expect(screen.getByLabelText('Grid view')).toBeInTheDocument();
    expect(screen.getByLabelText('List view')).toBeInTheDocument();
  });

  it('highlights the active view mode (grid)', () => {
    render(<ViewToggle viewMode="grid" onChange={onChange} />);
    expect(screen.getByLabelText('Grid view')).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByLabelText('List view')).toHaveAttribute('aria-pressed', 'false');
  });

  it('highlights the active view mode (list)', () => {
    render(<ViewToggle viewMode="list" onChange={onChange} />);
    expect(screen.getByLabelText('List view')).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByLabelText('Grid view')).toHaveAttribute('aria-pressed', 'false');
  });

  it('calls onChange when a different view mode is selected', async () => {
    const user = userEvent.setup();
    render(<ViewToggle viewMode="grid" onChange={onChange} />);
    await user.click(screen.getByLabelText('List view'));
    expect(onChange).toHaveBeenCalledWith('list');
  });

  it('does not call onChange when clicking the already-active mode', async () => {
    const user = userEvent.setup();
    render(<ViewToggle viewMode="grid" onChange={onChange} />);
    await user.click(screen.getByLabelText('Grid view'));
    // MUI ToggleButtonGroup with exclusive doesn't fire on deselect when enforceValue
    expect(onChange).not.toHaveBeenCalled();
  });
});
