import { render, screen } from '../../../../__tests__/test-utils';
import CatalogPagination from '../CatalogPagination';
import type { PaginationMeta } from '@apic-vibe-portal/shared';

describe('CatalogPagination', () => {
  const defaultPagination: PaginationMeta = {
    page: 1,
    pageSize: 20,
    totalCount: 50,
    totalPages: 3,
  };

  const onPageChange = jest.fn();
  const onPageSizeChange = jest.fn();

  beforeEach(() => {
    onPageChange.mockClear();
    onPageSizeChange.mockClear();
  });

  it('displays item count information', () => {
    render(
      <CatalogPagination
        pagination={defaultPagination}
        onPageChange={onPageChange}
        onPageSizeChange={onPageSizeChange}
      />
    );
    expect(screen.getByTestId('pagination-info')).toHaveTextContent('Showing 1–20 of 50 APIs');
  });

  it('renders pagination controls', () => {
    render(
      <CatalogPagination
        pagination={defaultPagination}
        onPageChange={onPageChange}
        onPageSizeChange={onPageSizeChange}
      />
    );
    // MUI Pagination renders numbered buttons
    expect(screen.getByRole('button', { name: /page 1/i })).toBeInTheDocument();
  });

  it('renders nothing when totalCount is 0', () => {
    const emptyPagination: PaginationMeta = { page: 1, pageSize: 20, totalCount: 0, totalPages: 0 };
    const { container } = render(
      <CatalogPagination
        pagination={emptyPagination}
        onPageChange={onPageChange}
        onPageSizeChange={onPageSizeChange}
      />
    );
    expect(container.firstChild).toBeNull();
  });

  it('shows correct range on page 2', () => {
    const page2: PaginationMeta = { page: 2, pageSize: 20, totalCount: 50, totalPages: 3 };
    render(
      <CatalogPagination pagination={page2} onPageChange={onPageChange} onPageSizeChange={onPageSizeChange} />
    );
    expect(screen.getByTestId('pagination-info')).toHaveTextContent('Showing 21–40 of 50 APIs');
  });

  it('shows correct range on last page', () => {
    const lastPage: PaginationMeta = { page: 3, pageSize: 20, totalCount: 50, totalPages: 3 };
    render(
      <CatalogPagination pagination={lastPage} onPageChange={onPageChange} onPageSizeChange={onPageSizeChange} />
    );
    expect(screen.getByTestId('pagination-info')).toHaveTextContent('Showing 41–50 of 50 APIs');
  });
});
