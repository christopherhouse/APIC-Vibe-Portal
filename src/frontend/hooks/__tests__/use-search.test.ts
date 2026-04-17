import { renderHook, act } from '@testing-library/react';
import { useSearch } from '../use-search';
import * as searchApi from '@/lib/search-api';
import { ApiKind, ApiLifecycle } from '@apic-vibe-portal/shared';

jest.mock('@/lib/search-api');

const mockFetchSearch = jest.mocked(searchApi.fetchSearch);

const mockResponse = {
  results: [
    {
      apiId: 'api-1',
      apiName: 'petstore',
      title: 'Petstore API',
      description: 'Manages pets',
      kind: ApiKind.REST,
      lifecycleStage: ApiLifecycle.Production,
      score: 0.9,
    },
  ],
  totalCount: 1,
  facets: { kind: [], lifecycle: [], tags: [] },
  queryDuration: 50,
};

describe('useSearch', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    mockFetchSearch.mockResolvedValue(mockResponse);
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.clearAllMocks();
  });

  it('returns empty state for blank query', async () => {
    const { result } = renderHook(() => useSearch({ query: '' }));
    await act(async () => jest.runAllTimers());
    expect(result.current.results).toHaveLength(0);
    expect(mockFetchSearch).not.toHaveBeenCalled();
  });

  it('does not fetch when disabled', async () => {
    const { result } = renderHook(() => useSearch({ query: 'petstore', enabled: false }));
    await act(async () => jest.runAllTimers());
    expect(result.current.results).toHaveLength(0);
    expect(mockFetchSearch).not.toHaveBeenCalled();
  });

  it('debounces and fetches after delay', async () => {
    renderHook(() => useSearch({ query: 'petstore', debounceMs: 300 }));

    expect(mockFetchSearch).not.toHaveBeenCalled();

    await act(async () => {
      jest.advanceTimersByTime(300);
      await Promise.resolve();
    });

    expect(mockFetchSearch).toHaveBeenCalledWith(
      expect.objectContaining({ query: 'petstore' }),
      expect.any(AbortSignal)
    );
  });

  it('populates results after successful fetch', async () => {
    const { result } = renderHook(() => useSearch({ query: 'petstore', debounceMs: 0 }));

    await act(async () => {
      jest.runAllTimers();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(result.current.results).toHaveLength(1);
    expect(result.current.totalCount).toBe(1);
  });

  it('sets error state on fetch failure', async () => {
    mockFetchSearch.mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useSearch({ query: 'petstore', debounceMs: 0 }));

    await act(async () => {
      jest.runAllTimers();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(result.current.error).toBe('Network error');
  });
});
