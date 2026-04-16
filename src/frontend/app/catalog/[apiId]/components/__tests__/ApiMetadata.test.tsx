import { render, screen } from '../../../../../__tests__/test-utils';
import type { ApiDefinition } from '@apic-vibe-portal/shared';
import { ApiKind, ApiLifecycle } from '@apic-vibe-portal/shared';
import ApiMetadata from '../ApiMetadata';

const baseApi: ApiDefinition = {
  id: 'api-1',
  name: 'petstore',
  title: 'Petstore API',
  description: 'A sample API for managing pets',
  kind: ApiKind.REST,
  lifecycleStage: ApiLifecycle.Production,
  versions: [],
  deployments: [],
  createdAt: '2026-01-01T00:00:00Z',
  updatedAt: '2026-03-15T10:00:00Z',
};

describe('ApiMetadata', () => {
  it('renders description', () => {
    render(<ApiMetadata api={baseApi} />);
    expect(screen.getByText('A sample API for managing pets')).toBeInTheDocument();
  });

  it('renders "No description available" when description is empty', () => {
    render(<ApiMetadata api={{ ...baseApi, description: '' }} />);
    expect(screen.getByText('No description available.')).toBeInTheDocument();
  });

  it('renders license when present', () => {
    render(<ApiMetadata api={{ ...baseApi, license: 'MIT' }} />);
    expect(screen.getByText('License')).toBeInTheDocument();
    expect(screen.getByText('MIT')).toBeInTheDocument();
  });

  it('renders terms of service when present', () => {
    render(
      <ApiMetadata api={{ ...baseApi, termsOfService: 'https://example.com/tos' }} />,
    );
    expect(screen.getByText('Terms of Service')).toBeInTheDocument();
    expect(screen.getByText('https://example.com/tos')).toBeInTheDocument();
  });

  it('renders contacts when present', () => {
    render(
      <ApiMetadata
        api={{
          ...baseApi,
          contacts: [
            { name: 'John Doe', email: 'john@example.com', url: 'https://john.example.com' },
          ],
        }}
      />,
    );
    expect(screen.getByText('Contacts')).toBeInTheDocument();
    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('john@example.com')).toBeInTheDocument();
  });

  it('renders external docs when present', () => {
    render(
      <ApiMetadata
        api={{
          ...baseApi,
          externalDocs: [
            { title: 'API Guide', url: 'https://docs.example.com', description: 'Full guide' },
          ],
        }}
      />,
    );
    expect(screen.getByText('External Documentation')).toBeInTheDocument();
    expect(screen.getByText('API Guide')).toBeInTheDocument();
    expect(screen.getByText('Full guide')).toBeInTheDocument();
  });

  it('renders custom properties when present', () => {
    render(
      <ApiMetadata
        api={{ ...baseApi, customProperties: { team: 'Platform', region: 'US-East' } }}
      />,
    );
    expect(screen.getByText('Custom Properties')).toBeInTheDocument();
    expect(screen.getByText('team')).toBeInTheDocument();
    expect(screen.getByText('Platform')).toBeInTheDocument();
  });

  it('has correct data-testid', () => {
    render(<ApiMetadata api={baseApi} />);
    expect(screen.getByTestId('api-metadata')).toBeInTheDocument();
  });
});
