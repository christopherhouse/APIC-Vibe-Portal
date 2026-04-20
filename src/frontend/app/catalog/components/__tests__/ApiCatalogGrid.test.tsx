import { render, screen } from '../../../../__tests__/test-utils';
import ApiCatalogGrid from '../ApiCatalogGrid';
import type { ApiCatalogItem } from '@apic-vibe-portal/shared';
import { ApiKind, ApiLifecycle } from '@apic-vibe-portal/shared';

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

const mockApis: ApiCatalogItem[] = [
  {
    id: 'api-1',
    name: 'petstore',
    title: 'Petstore API',
    description: 'Manage pets',
    kind: ApiKind.REST,
    lifecycleStage: ApiLifecycle.Production,
    versionCount: 3,
    deploymentCount: 2,
    updatedAt: '2026-03-15T10:00:00Z',
  },
  {
    id: 'api-2',
    name: 'users',
    title: 'Users API',
    description: 'Manage users',
    kind: ApiKind.GraphQL,
    lifecycleStage: ApiLifecycle.Development,
    versionCount: 1,
    deploymentCount: 0,
    updatedAt: '2026-03-14T10:00:00Z',
  },
];

describe('ApiCatalogGrid', () => {
  it('renders APIs in grid mode', () => {
    render(<ApiCatalogGrid items={mockApis} viewMode="grid" />);
    expect(screen.getByTestId('catalog-grid')).toBeInTheDocument();
    expect(screen.getByText('Petstore API')).toBeInTheDocument();
    expect(screen.getByText('Users API')).toBeInTheDocument();
  });

  it('renders APIs in list mode', () => {
    render(<ApiCatalogGrid items={mockApis} viewMode="list" />);
    expect(screen.getByTestId('catalog-list')).toBeInTheDocument();
    expect(screen.getByText('Petstore API')).toBeInTheDocument();
    expect(screen.getByText('Users API')).toBeInTheDocument();
  });

  it('shows empty state when no items', () => {
    render(<ApiCatalogGrid items={[]} viewMode="grid" />);
    expect(screen.getByTestId('catalog-empty-state')).toBeInTheDocument();
    expect(screen.getByText('No APIs found')).toBeInTheDocument();
    expect(screen.getByText(/Try adjusting your filters/)).toBeInTheDocument();
  });
});
