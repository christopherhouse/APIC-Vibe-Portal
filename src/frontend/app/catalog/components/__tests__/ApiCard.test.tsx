import { render, screen } from '../../../../__tests__/test-utils';
import userEvent from '@testing-library/user-event';
import ApiCard from '../ApiCard';
import type { ApiCatalogItem } from '@apic-vibe-portal/shared';
import { ApiKind, ApiLifecycle } from '@apic-vibe-portal/shared';

const mockPush = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}));

const mockApi: ApiCatalogItem = {
  id: 'api-1',
  name: 'petstore',
  title: 'Petstore API',
  description: 'A sample API for managing pets in the store with CRUD operations',
  kind: ApiKind.REST,
  lifecycleStage: ApiLifecycle.Production,
  versionCount: 3,
  deploymentCount: 2,
  updatedAt: '2026-03-15T10:00:00Z',
};

describe('ApiCard', () => {
  beforeEach(() => {
    mockPush.mockClear();
  });

  it('renders API title and description in grid mode', () => {
    render(<ApiCard api={mockApi} />);
    expect(screen.getByText('Petstore API')).toBeInTheDocument();
    expect(screen.getByText(/A sample API for managing pets/)).toBeInTheDocument();
  });

  it('renders kind and lifecycle badges', () => {
    render(<ApiCard api={mockApi} />);
    expect(screen.getByText('REST')).toBeInTheDocument();
    expect(screen.getByText('Production')).toBeInTheDocument();
  });

  it('renders version count', () => {
    render(<ApiCard api={mockApi} />);
    expect(screen.getByText('3 versions')).toBeInTheDocument();
  });

  it('renders updated date', () => {
    render(<ApiCard api={mockApi} />);
    expect(screen.getByText(/Updated/)).toBeInTheDocument();
  });

  it('navigates to detail page on click', async () => {
    const user = userEvent.setup();
    render(<ApiCard api={mockApi} />);
    await user.click(screen.getByText('Petstore API'));
    expect(mockPush).toHaveBeenCalledWith('/catalog/api-1');
  });

  it('renders in list mode', () => {
    render(<ApiCard api={mockApi} listMode />);
    expect(screen.getByText('Petstore API')).toBeInTheDocument();
    expect(screen.getByText('REST')).toBeInTheDocument();
    expect(screen.getByText('Production')).toBeInTheDocument();
  });

  it('has proper test id', () => {
    render(<ApiCard api={mockApi} />);
    expect(screen.getByTestId('api-card-api-1')).toBeInTheDocument();
  });

  it('shows singular version when count is 1', () => {
    const singleVersion = { ...mockApi, versionCount: 1 };
    render(<ApiCard api={singleVersion} />);
    expect(screen.getByText('1 version')).toBeInTheDocument();
  });
});
