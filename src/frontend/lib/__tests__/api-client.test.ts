import { setTokenProvider, apiClient, ApiError } from '../api-client';

// Mock global fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

describe('api-client', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('setTokenProvider', () => {
    it('injects Bearer token into requests when provider is set', async () => {
      setTokenProvider(async () => 'test-token-123');

      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ data: 'test' }),
      });

      await apiClient.get('/api/test');

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [, options] = mockFetch.mock.calls[0];
      expect(options.headers['Authorization']).toBe('Bearer test-token-123');
    });

    it('does not inject token when provider returns null', async () => {
      setTokenProvider(async () => null);

      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ data: 'test' }),
      });

      await apiClient.get('/api/test');

      const [, options] = mockFetch.mock.calls[0];
      expect(options.headers['Authorization']).toBeUndefined();
    });
  });

  describe('error handling', () => {
    it('throws ApiError for non-ok responses', async () => {
      setTokenProvider(async () => null);
      mockFetch.mockResolvedValue({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: async () => ({ error: 'Not authenticated' }),
      });

      await expect(apiClient.get('/api/test')).rejects.toThrow(ApiError);
    });
  });
});
