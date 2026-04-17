import { render, screen } from '../../../../__tests__/test-utils';
import { ApiKind, ApiLifecycle } from '@apic-vibe-portal/shared';
import type { SearchResultItem } from '@/lib/search-api';
import SearchResults from '../SearchResults';

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

const makeResult = (id: string): SearchResultItem => ({
  apiId: id,
  apiName: id,
  title: `API ${id}`,
  description: `Description for ${id}`,
  kind: ApiKind.REST,
  lifecycleStage: ApiLifecycle.Production,
  score: 0.9,
});

describe('SearchResults', () => {
  it('renders skeleton when loading', () => {
    render(<SearchResults results={[]} isLoading={true} />);
    expect(screen.getByTestId('search-results-loading')).toBeInTheDocument();
    expect(screen.getAllByTestId('search-result-skeleton').length).toBeGreaterThan(0);
  });

  it('renders result cards when not loading', () => {
    const results = [makeResult('api-1'), makeResult('api-2')];
    render(<SearchResults results={results} isLoading={false} />);
    expect(screen.getByTestId('search-results')).toBeInTheDocument();
    expect(screen.getByTestId('search-result-api-1')).toBeInTheDocument();
    expect(screen.getByTestId('search-result-api-2')).toBeInTheDocument();
  });

  it('renders empty list when no results', () => {
    render(<SearchResults results={[]} isLoading={false} />);
    expect(screen.getByTestId('search-results')).toBeInTheDocument();
    expect(screen.queryByTestId('search-result-skeleton')).not.toBeInTheDocument();
  });
});
