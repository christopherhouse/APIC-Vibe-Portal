import { render, screen, fireEvent } from '../../../../../__tests__/test-utils';
import type { ApiVersion } from '@apic-vibe-portal/shared';
import { ApiLifecycle } from '@apic-vibe-portal/shared';
import ApiVersionList from '../ApiVersionList';

const mockVersions: ApiVersion[] = [
  {
    id: 'v1',
    name: 'v1',
    title: 'Version 1.0',
    lifecycleStage: ApiLifecycle.Production,
    createdAt: '2026-01-01T00:00:00Z',
    updatedAt: '2026-03-01T00:00:00Z',
  },
  {
    id: 'v2',
    name: 'v2',
    title: 'Version 2.0',
    lifecycleStage: ApiLifecycle.Development,
    createdAt: '2026-02-01T00:00:00Z',
    updatedAt: '2026-03-15T00:00:00Z',
  },
];

describe('ApiVersionList', () => {
  const mockOnChange = jest.fn();

  beforeEach(() => {
    mockOnChange.mockClear();
  });

  it('renders loading skeleton when isLoading', () => {
    render(
      <ApiVersionList
        versions={[]}
        selectedVersionId={null}
        onVersionChange={mockOnChange}
        isLoading
      />
    );
    expect(screen.getByTestId('version-list-skeleton')).toBeInTheDocument();
  });

  it('renders empty state when no versions', () => {
    render(
      <ApiVersionList versions={[]} selectedVersionId={null} onVersionChange={mockOnChange} />
    );
    expect(screen.getByTestId('version-list-empty')).toBeInTheDocument();
    expect(screen.getByText('No versions available for this API.')).toBeInTheDocument();
  });

  it('renders version table with versions', () => {
    render(
      <ApiVersionList
        versions={mockVersions}
        selectedVersionId="v1"
        onVersionChange={mockOnChange}
      />
    );
    expect(screen.getByTestId('version-list')).toBeInTheDocument();
    expect(screen.getByTestId('version-row-v1')).toBeInTheDocument();
    expect(screen.getByTestId('version-row-v2')).toBeInTheDocument();
  });

  it('renders lifecycle badges', () => {
    render(
      <ApiVersionList
        versions={mockVersions}
        selectedVersionId="v1"
        onVersionChange={mockOnChange}
      />
    );
    expect(screen.getByText('Production')).toBeInTheDocument();
    expect(screen.getByText('Development')).toBeInTheDocument();
  });

  it('calls onVersionChange when row is clicked', () => {
    render(
      <ApiVersionList
        versions={mockVersions}
        selectedVersionId="v1"
        onVersionChange={mockOnChange}
      />
    );
    fireEvent.click(screen.getByTestId('version-row-v2'));
    expect(mockOnChange).toHaveBeenCalledWith('v2');
  });

  it('shows version rows with correct test ids', () => {
    render(
      <ApiVersionList
        versions={mockVersions}
        selectedVersionId="v1"
        onVersionChange={mockOnChange}
      />
    );
    expect(screen.getByTestId('version-row-v1')).toBeInTheDocument();
    expect(screen.getByTestId('version-row-v2')).toBeInTheDocument();
  });
});
