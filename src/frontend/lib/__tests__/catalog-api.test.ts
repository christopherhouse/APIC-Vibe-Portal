import { fetchCatalogApis } from '@/lib/catalog-api';
import { apiClient } from '@/lib/api-client';

// Mock apiClient
jest.mock('@/lib/api-client', () => ({
  apiClient: {
    get: jest.fn(),
  },
}));

const mockGet = apiClient.get as jest.Mock;

describe('fetchCatalogApis', () => {
  beforeEach(() => {
    mockGet.mockClear();
  });

  const mockBffResponse = {
    data: [
      {
        id: 'api-1',
        name: 'test',
        title: 'Test API',
        description: 'A test API',
        kind: 'rest',
        lifecycleStage: 'production',
        versions: [
          {
            id: 'v1',
            name: 'v1',
            title: 'v1',
            lifecycle_stage: 'production',
            created_at: '2026-01-01',
            updated_at: '2026-01-01',
          },
        ],
        deployments: [],
        createdAt: '2026-01-01T00:00:00Z',
        updatedAt: '2026-01-01T00:00:00Z',
      },
    ],
    meta: { page: 1, pageSize: 20, totalCount: 1, totalPages: 1 },
  };

  it('fetches with default parameters', async () => {
    mockGet.mockResolvedValue(mockBffResponse);

    const result = await fetchCatalogApis();
    expect(mockGet).toHaveBeenCalledTimes(1);
    expect(mockGet).toHaveBeenCalledWith('/api/catalog', { params: {} });
    expect(result.data).toHaveLength(1);
    expect(result.data[0].versionCount).toBe(1);
    expect(result.data[0].deploymentCount).toBe(0);
  });

  it('includes page and pageSize params', async () => {
    mockGet.mockResolvedValue(mockBffResponse);

    await fetchCatalogApis({ page: 2, pageSize: 50 });
    expect(mockGet).toHaveBeenCalledWith('/api/catalog', {
      params: expect.objectContaining({ page: '2', pageSize: '50' }),
    });
  });

  it('includes sort and direction params', async () => {
    mockGet.mockResolvedValue(mockBffResponse);

    await fetchCatalogApis({ sort: 'name', direction: 'asc' });
    expect(mockGet).toHaveBeenCalledWith('/api/catalog', {
      params: expect.objectContaining({ sort: 'name', direction: 'asc' }),
    });
  });

  it('includes lifecycle filter', async () => {
    mockGet.mockResolvedValue(mockBffResponse);

    await fetchCatalogApis({ lifecycle: 'production' });
    expect(mockGet).toHaveBeenCalledWith('/api/catalog', {
      params: expect.objectContaining({ lifecycle: 'production' }),
    });
  });

  it('includes kind filter', async () => {
    mockGet.mockResolvedValue(mockBffResponse);

    await fetchCatalogApis({ kind: 'rest' });
    expect(mockGet).toHaveBeenCalledWith('/api/catalog', {
      params: expect.objectContaining({ kind: 'rest' }),
    });
  });

  it('maps ApiDefinition to ApiCatalogItem', async () => {
    mockGet.mockResolvedValue(mockBffResponse);

    const result = await fetchCatalogApis();
    const item = result.data[0];
    expect(item).toEqual(
      expect.objectContaining({
        id: 'api-1',
        name: 'test',
        title: 'Test API',
        versionCount: 1,
        deploymentCount: 0,
      })
    );
    // Should not contain raw arrays
    expect(item).not.toHaveProperty('versions');
    expect(item).not.toHaveProperty('deployments');
  });

  it('propagates errors from apiClient', async () => {
    mockGet.mockRejectedValue(new Error('API request failed: 500 Internal Server Error'));

    await expect(fetchCatalogApis()).rejects.toThrow(
      'API request failed: 500 Internal Server Error'
    );
  });
});
