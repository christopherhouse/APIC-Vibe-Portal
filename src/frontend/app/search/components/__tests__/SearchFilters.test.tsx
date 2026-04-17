import { render, screen } from '../../../../__tests__/test-utils';
import userEvent from '@testing-library/user-event';
import SearchFilters from '../SearchFilters';
import type { SearchFacets } from '@/lib/search-api';

const defaultProps = {
  selectedLifecycle: undefined as string | undefined,
  selectedKind: undefined as string | undefined,
  facets: undefined as SearchFacets | undefined,
  onLifecycleChange: jest.fn(),
  onKindChange: jest.fn(),
};

describe('SearchFilters', () => {
  beforeEach(() => {
    defaultProps.onLifecycleChange.mockClear();
    defaultProps.onKindChange.mockClear();
  });

  it('renders lifecycle filter options', () => {
    render(<SearchFilters {...defaultProps} />);
    expect(screen.getByText('Lifecycle Stage')).toBeInTheDocument();
    expect(screen.getByText('Production')).toBeInTheDocument();
    expect(screen.getByText('Deprecated')).toBeInTheDocument();
  });

  it('renders kind filter options', () => {
    render(<SearchFilters {...defaultProps} />);
    expect(screen.getByText('API Kind')).toBeInTheDocument();
    expect(screen.getByText('REST')).toBeInTheDocument();
    expect(screen.getByText('GraphQL')).toBeInTheDocument();
  });

  it('calls onLifecycleChange when a lifecycle radio is selected', async () => {
    const user = userEvent.setup();
    render(<SearchFilters {...defaultProps} />);
    await user.click(screen.getByLabelText('Filter by Production'));
    expect(defaultProps.onLifecycleChange).toHaveBeenCalledWith('production');
  });

  it('calls onKindChange when a kind radio is selected', async () => {
    const user = userEvent.setup();
    render(<SearchFilters {...defaultProps} />);
    await user.click(screen.getByLabelText('Filter by REST'));
    expect(defaultProps.onKindChange).toHaveBeenCalledWith('rest');
  });

  it('shows clear all button when a filter is active', () => {
    render(<SearchFilters {...defaultProps} selectedLifecycle="production" />);
    expect(screen.getByText('Clear all')).toBeInTheDocument();
  });

  it('does not show clear all when no filters are active', () => {
    render(<SearchFilters {...defaultProps} />);
    expect(screen.queryByText('Clear all')).not.toBeInTheDocument();
  });

  it('clears all filters when clear all is clicked', async () => {
    const user = userEvent.setup();
    render(<SearchFilters {...defaultProps} selectedLifecycle="production" selectedKind="rest" />);
    await user.click(screen.getByText('Clear all'));
    expect(defaultProps.onLifecycleChange).toHaveBeenCalledWith(undefined);
    expect(defaultProps.onKindChange).toHaveBeenCalledWith(undefined);
  });

  it('displays facet counts when facets are provided', () => {
    const facets: SearchFacets = {
      kind: [{ value: 'rest', count: 7 }],
      lifecycle: [{ value: 'production', count: 3 }],
      tags: [],
    };
    render(<SearchFilters {...defaultProps} facets={facets} />);
    expect(screen.getByTestId('facet-kind-rest')).toBeInTheDocument();
    expect(screen.getByTestId('facet-lifecycle-production')).toBeInTheDocument();
  });
});
