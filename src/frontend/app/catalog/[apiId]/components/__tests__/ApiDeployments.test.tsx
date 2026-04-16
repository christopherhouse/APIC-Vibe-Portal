import { render, screen } from '../../../../../__tests__/test-utils';
import type { ApiDeployment } from '@apic-vibe-portal/shared';
import { EnvironmentKind } from '@apic-vibe-portal/shared';
import ApiDeployments from '../ApiDeployments';

const mockDeployments: ApiDeployment[] = [
  {
    id: 'dep-1',
    title: 'Production US',
    environment: {
      id: 'env-1',
      name: 'prod-us',
      title: 'Production US',
      kind: EnvironmentKind.Production,
    },
    server: {
      runtimeUri: ['https://api.example.com', 'https://api-secondary.example.com'],
    },
    createdAt: '2026-01-01T00:00:00Z',
    updatedAt: '2026-03-15T10:00:00Z',
  },
  {
    id: 'dep-2',
    title: 'Staging EU',
    environment: {
      id: 'env-2',
      name: 'staging-eu',
      title: 'Staging EU',
      kind: EnvironmentKind.Staging,
    },
    server: {
      runtimeUri: ['https://staging.api.example.com'],
    },
    createdAt: '2026-01-15T00:00:00Z',
    updatedAt: '2026-03-10T08:00:00Z',
  },
];

describe('ApiDeployments', () => {
  it('renders loading skeleton when isLoading', () => {
    render(<ApiDeployments deployments={[]} isLoading />);
    expect(screen.getByTestId('deployments-skeleton')).toBeInTheDocument();
  });

  it('renders empty state when no deployments', () => {
    render(<ApiDeployments deployments={[]} />);
    expect(screen.getByTestId('deployments-empty')).toBeInTheDocument();
    expect(screen.getByText('No deployments found for this API.')).toBeInTheDocument();
  });

  it('renders deployment table', () => {
    render(<ApiDeployments deployments={mockDeployments} />);
    expect(screen.getByTestId('deployments-table')).toBeInTheDocument();
  });

  it('renders deployment titles', () => {
    render(<ApiDeployments deployments={mockDeployments} />);
    expect(screen.getByTestId('deployment-row-dep-1')).toBeInTheDocument();
    expect(screen.getByTestId('deployment-row-dep-2')).toBeInTheDocument();
  });

  it('renders server URLs as links', () => {
    render(<ApiDeployments deployments={mockDeployments} />);
    const link = screen.getByText('https://api.example.com');
    expect(link.closest('a')).toHaveAttribute('href', 'https://api.example.com');
    expect(link.closest('a')).toHaveAttribute('target', '_blank');
  });

  it('renders multiple URIs for a deployment', () => {
    render(<ApiDeployments deployments={mockDeployments} />);
    expect(screen.getByText('https://api.example.com')).toBeInTheDocument();
    expect(screen.getByText('https://api-secondary.example.com')).toBeInTheDocument();
  });

  it('renders deployment rows with correct test ids', () => {
    render(<ApiDeployments deployments={mockDeployments} />);
    expect(screen.getByTestId('deployment-row-dep-1')).toBeInTheDocument();
    expect(screen.getByTestId('deployment-row-dep-2')).toBeInTheDocument();
  });
});
