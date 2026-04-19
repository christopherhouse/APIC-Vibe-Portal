import { render, screen } from '../../../../../__tests__/test-utils';
import PoliciesTable from '../PoliciesTable';
import type { AccessPolicy } from '@/lib/admin-api';

const noop = jest.fn();

const mockPolicies: AccessPolicy[] = [
  {
    apiName: 'petstore-api',
    apiId: '',
    allowedGroups: ['grp-1', 'grp-2'],
    isPublic: false,
    createdAt: '2026-01-01T00:00:00Z',
    updatedAt: '2026-03-15T00:00:00Z',
  },
  {
    apiName: 'public-api',
    apiId: '',
    allowedGroups: [],
    isPublic: true,
    createdAt: '2026-01-01T00:00:00Z',
    updatedAt: '2026-01-02T00:00:00Z',
  },
  {
    apiName: 'locked-api',
    apiId: '',
    allowedGroups: [],
    isPublic: false,
    createdAt: '2026-01-01T00:00:00Z',
    updatedAt: '2026-01-02T00:00:00Z',
  },
];

describe('PoliciesTable', () => {
  it('renders skeleton while loading', () => {
    render(<PoliciesTable policies={[]} isLoading onEdit={noop} onDelete={noop} />);
    expect(screen.getByTestId('policies-table-skeleton')).toBeInTheDocument();
  });

  it('renders empty state when no policies', () => {
    render(<PoliciesTable policies={[]} isLoading={false} onEdit={noop} onDelete={noop} />);
    expect(screen.getByTestId('policies-empty-state')).toBeInTheDocument();
  });

  it('renders a row for each policy', () => {
    render(<PoliciesTable policies={mockPolicies} isLoading={false} onEdit={noop} onDelete={noop} />);
    expect(screen.getByTestId('policy-row-petstore-api')).toBeInTheDocument();
    expect(screen.getByTestId('policy-row-public-api')).toBeInTheDocument();
    expect(screen.getByTestId('policy-row-locked-api')).toBeInTheDocument();
  });

  it('shows Public chip for isPublic policies', () => {
    render(<PoliciesTable policies={mockPolicies} isLoading={false} onEdit={noop} onDelete={noop} />);
    expect(screen.getByText('Public')).toBeInTheDocument();
  });

  it('shows Restricted chip for group-restricted policies', () => {
    render(<PoliciesTable policies={mockPolicies} isLoading={false} onEdit={noop} onDelete={noop} />);
    // petstore-api and locked-api are restricted
    const restrictedChips = screen.getAllByText('Restricted');
    expect(restrictedChips.length).toBeGreaterThanOrEqual(1);
  });

  it('shows groups as chips for restricted policies', () => {
    render(<PoliciesTable policies={mockPolicies} isLoading={false} onEdit={noop} onDelete={noop} />);
    expect(screen.getByText('grp-1')).toBeInTheDocument();
    expect(screen.getByText('grp-2')).toBeInTheDocument();
  });

  it('shows inaccessible warning for locked API', () => {
    render(<PoliciesTable policies={mockPolicies} isLoading={false} onEdit={noop} onDelete={noop} />);
    expect(screen.getByText(/No groups — API inaccessible/)).toBeInTheDocument();
  });

  it('calls onEdit when edit button is clicked', async () => {
    render(
      <PoliciesTable policies={mockPolicies} isLoading={false} onEdit={noop} onDelete={noop} />
    );
    const editButton = screen.getByTestId('edit-policy-petstore-api');
    editButton.click();
    expect(noop).toHaveBeenCalledWith(mockPolicies[0]);
  });

  it('calls onDelete when delete button is clicked', () => {
    render(<PoliciesTable policies={mockPolicies} isLoading={false} onEdit={noop} onDelete={noop} />);
    const deleteButton = screen.getByTestId('delete-policy-petstore-api');
    deleteButton.click();
    expect(noop).toHaveBeenCalledWith(mockPolicies[0]);
  });
});
