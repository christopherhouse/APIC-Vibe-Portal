import { render, screen } from '../../../../__tests__/test-utils';
import userEvent from '@testing-library/user-event';
import SearchModeToggle from '../SearchModeToggle';
import type { SearchMode } from '@/lib/search-api';

describe('SearchModeToggle', () => {
  it('renders all three mode options', () => {
    const onChange = jest.fn();
    render(<SearchModeToggle mode="hybrid" onChange={onChange} />);
    expect(screen.getByRole('button', { name: /keyword search mode/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /semantic search mode/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /hybrid search mode/i })).toBeInTheDocument();
  });

  it('marks the current mode as selected', () => {
    render(<SearchModeToggle mode="semantic" onChange={jest.fn()} />);
    // MUI ToggleButton has aria-pressed="true" when selected
    const semanticBtn = screen.getByRole('button', { name: /semantic search mode/i });
    expect(semanticBtn).toHaveAttribute('aria-pressed', 'true');
  });

  it('calls onChange when a different mode is clicked', async () => {
    const onChange = jest.fn();
    const user = userEvent.setup();
    render(<SearchModeToggle mode="hybrid" onChange={onChange} />);
    await user.click(screen.getByRole('button', { name: /keyword search mode/i }));
    expect(onChange).toHaveBeenCalledWith('keyword' satisfies SearchMode);
  });

  it('renders the data-testid container', () => {
    render(<SearchModeToggle mode="hybrid" onChange={jest.fn()} />);
    expect(screen.getByTestId('search-mode-toggle')).toBeInTheDocument();
  });
});
