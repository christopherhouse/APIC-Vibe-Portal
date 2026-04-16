import { render, screen } from '../../../../../__tests__/test-utils';
import type { ApiDefinition } from '@apic-vibe-portal/shared';
import { ApiKind, ApiLifecycle } from '@apic-vibe-portal/shared';
import ApiHeader from '../ApiHeader';

jest.mock('next/link', () => {
  return function MockNextLink({ children, href }: { children: React.ReactNode; href: string }) {
    return <a href={href}>{children}</a>;
  };
});

const mockApi: ApiDefinition = {
  id: 'api-1',
  name: 'petstore',
  title: 'Petstore API',
  description: 'A sample API for managing pets',
  kind: ApiKind.REST,
  lifecycleStage: ApiLifecycle.Production,
  versions: [],
  deployments: [],
  termsOfService: 'https://example.com/tos',
  license: 'MIT',
  contacts: [],
  externalDocs: [],
  createdAt: '2026-01-01T00:00:00Z',
  updatedAt: '2026-03-15T10:00:00Z',
};

describe('ApiHeader', () => {
  it('renders loading skeleton when isLoading is true', () => {
    render(<ApiHeader api={null} isLoading />);
    expect(screen.getByTestId('api-header-skeleton')).toBeInTheDocument();
  });

  it('renders loading skeleton when api is null', () => {
    render(<ApiHeader api={null} />);
    expect(screen.getByTestId('api-header-skeleton')).toBeInTheDocument();
  });

  it('renders API title as heading', () => {
    render(<ApiHeader api={mockApi} />);
    expect(screen.getByRole('heading', { name: 'Petstore API' })).toBeInTheDocument();
  });

  it('renders breadcrumb with catalog link', () => {
    render(<ApiHeader api={mockApi} />);
    expect(screen.getByText('Catalog')).toBeInTheDocument();
    const catalogLink = screen.getByText('Catalog').closest('a');
    expect(catalogLink).toHaveAttribute('href', '/catalog');
  });

  it('renders kind badge', () => {
    render(<ApiHeader api={mockApi} />);
    expect(screen.getByTestId('kind-badge')).toHaveTextContent('REST');
  });

  it('renders lifecycle badge', () => {
    render(<ApiHeader api={mockApi} />);
    expect(screen.getByTestId('lifecycle-badge')).toHaveTextContent('Production');
  });

  it('renders description', () => {
    render(<ApiHeader api={mockApi} />);
    expect(screen.getByText('A sample API for managing pets')).toBeInTheDocument();
  });

  it('renders last updated date', () => {
    render(<ApiHeader api={mockApi} />);
    expect(screen.getByText(/Last updated/)).toBeInTheDocument();
  });
});
