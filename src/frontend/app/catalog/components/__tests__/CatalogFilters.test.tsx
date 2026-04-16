import { render, screen } from '../../../../__tests__/test-utils';
import userEvent from '@testing-library/user-event';
import CatalogFilters from '../CatalogFilters';

describe('CatalogFilters', () => {
  const defaultProps = {
    selectedLifecycle: undefined as string | undefined,
    selectedKind: undefined as string | undefined,
    onLifecycleChange: jest.fn(),
    onKindChange: jest.fn(),
  };

  beforeEach(() => {
    defaultProps.onLifecycleChange.mockClear();
    defaultProps.onKindChange.mockClear();
  });

  it('renders lifecycle filter options', () => {
    render(<CatalogFilters {...defaultProps} />);
    expect(screen.getByText('Lifecycle Stage')).toBeInTheDocument();
    expect(screen.getByText('Production')).toBeInTheDocument();
    expect(screen.getByText('Deprecated')).toBeInTheDocument();
    expect(screen.getByText('Retired')).toBeInTheDocument();
  });

  it('renders kind filter options', () => {
    render(<CatalogFilters {...defaultProps} />);
    expect(screen.getByText('API Kind')).toBeInTheDocument();
    expect(screen.getByText('REST')).toBeInTheDocument();
    expect(screen.getByText('GraphQL')).toBeInTheDocument();
    expect(screen.getByText('gRPC')).toBeInTheDocument();
  });

  it('calls onLifecycleChange when lifecycle radio is selected', async () => {
    const user = userEvent.setup();
    render(<CatalogFilters {...defaultProps} />);
    await user.click(screen.getByLabelText('Filter by Production'));
    expect(defaultProps.onLifecycleChange).toHaveBeenCalledWith('production');
  });

  it('calls onKindChange when kind radio is selected', async () => {
    const user = userEvent.setup();
    render(<CatalogFilters {...defaultProps} />);
    await user.click(screen.getByLabelText('Filter by REST'));
    expect(defaultProps.onKindChange).toHaveBeenCalledWith('rest');
  });

  it('shows selected lifecycle radio as checked', () => {
    render(<CatalogFilters {...defaultProps} selectedLifecycle="production" />);
    expect(screen.getByRole('radio', { name: 'Filter by Production' })).toBeChecked();
    expect(screen.getByRole('radio', { name: 'Filter by Design' })).not.toBeChecked();
  });

  it('shows clear all button when filters are active', () => {
    render(<CatalogFilters {...defaultProps} selectedLifecycle="production" />);
    expect(screen.getByText('Clear all')).toBeInTheDocument();
  });

  it('does not show clear all button when no filters are active', () => {
    render(<CatalogFilters {...defaultProps} />);
    expect(screen.queryByText('Clear all')).not.toBeInTheDocument();
  });

  it('clears all filters when clear all is clicked', async () => {
    const user = userEvent.setup();
    render(<CatalogFilters {...defaultProps} selectedLifecycle="production" selectedKind="rest" />);
    await user.click(screen.getByText('Clear all'));
    expect(defaultProps.onLifecycleChange).toHaveBeenCalledWith(undefined);
    expect(defaultProps.onKindChange).toHaveBeenCalledWith(undefined);
  });
});
