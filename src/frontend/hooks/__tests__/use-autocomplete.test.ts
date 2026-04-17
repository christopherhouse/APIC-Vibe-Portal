import { renderHook, act } from '@testing-library/react';
import { useAutocomplete } from '../use-autocomplete';
import * as searchApi from '@/lib/search-api';
import { ApiKind } from '@apic-vibe-portal/shared';

jest.mock('@/lib/search-api');

const mockFetchSuggestions = jest.mocked(searchApi.fetchSuggestions);

describe('useAutocomplete', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    mockFetchSuggestions.mockResolvedValue({
      suggestions: [
        {
          apiId: 'api-1',
          title: 'Petstore API',
          description: 'Manages pets',
          kind: ApiKind.REST,
        },
      ],
    });
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.clearAllMocks();
  });

  it('returns empty suggestions for short queries', async () => {
    const { result } = renderHook(() => useAutocomplete({ query: 'a', minChars: 2 }));
    act(() => jest.runAllTimers());
    expect(result.current.suggestions).toHaveLength(0);
    expect(mockFetchSuggestions).not.toHaveBeenCalled();
  });

  it('debounces and fetches suggestions when query is long enough', async () => {
    renderHook(() => useAutocomplete({ query: 'pet', minChars: 2, debounceMs: 300 }));

    expect(mockFetchSuggestions).not.toHaveBeenCalled();

    await act(async () => {
      jest.advanceTimersByTime(300);
    });

    expect(mockFetchSuggestions).toHaveBeenCalledWith('pet', expect.any(AbortSignal));
  });

  it('returns empty when disabled', async () => {
    const { result } = renderHook(() => useAutocomplete({ query: 'petstore', enabled: false }));
    act(() => jest.runAllTimers());
    expect(result.current.suggestions).toHaveLength(0);
    expect(mockFetchSuggestions).not.toHaveBeenCalled();
  });
});
