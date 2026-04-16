import { render, screen } from '../../../../__tests__/test-utils';
import userEvent from '@testing-library/user-event';
import CatalogSort from '../CatalogSort';

describe('CatalogSort', () => {
  const onSortChange = jest.fn();

  beforeEach(() => {
    onSortChange.mockClear();
  });

  it('renders the sort select', () => {
    render(<CatalogSort sort="updatedAt" direction="desc" onSortChange={onSortChange} />);
    expect(screen.getByLabelText('Sort by')).toBeInTheDocument();
  });

  it('displays current sort value', () => {
    render(<CatalogSort sort="name" direction="asc" onSortChange={onSortChange} />);
    // MUI Select renders the selected value as text inside the component
    expect(screen.getByText('Name (A–Z)')).toBeInTheDocument();
  });

  it('calls onSortChange when option is selected', async () => {
    const user = userEvent.setup();
    render(<CatalogSort sort="updatedAt" direction="desc" onSortChange={onSortChange} />);

    // Open the select dropdown
    await user.click(screen.getByRole('combobox'));
    // Click a menu item
    await user.click(screen.getByText('Name (A–Z)'));
    expect(onSortChange).toHaveBeenCalledWith('name', 'asc');
  });
});
