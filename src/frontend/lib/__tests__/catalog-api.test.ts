import { fetchCatalogApis } from '@/lib/catalog-api';

// Mock global fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

describe('fetchCatalogApis', () => {
  beforeEach(() => {
    mockFetch.mockClear();
  });

  const mockResponse = {
    data: [{ id: 'api-1', name: 'test', title: 'Test API' }],
    meta: { page: 1, pageSize: 20, totalCount: 1, totalPages: 1 },
  };

  it('fetches with default parameters', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    const result = await fetchCatalogApis();
    expect(mockFetch).toHaveBeenCalledTimes(1);
    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).toContain('/api/catalog');
    expect(result).toEqual(mockResponse);
  });

  it('includes page and pageSize params', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    await fetchCatalogApis({ page: 2, pageSize: 50 });
    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).toContain('page=2');
    expect(url).toContain('pageSize=50');
  });

  it('includes sort and direction params', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    await fetchCatalogApis({ sort: 'name', direction: 'asc' });
    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).toContain('sort=name');
    expect(url).toContain('direction=asc');
  });

  it('includes lifecycle filter', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    await fetchCatalogApis({ lifecycle: ['production'] });
    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).toContain('lifecycle=production');
  });

  it('includes kind filter', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    await fetchCatalogApis({ kind: ['rest'] });
    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).toContain('kind=rest');
  });

  it('throws on non-ok response', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
    });

    await expect(fetchCatalogApis()).rejects.toThrow('Catalog API error: 500 Internal Server Error');
  });
});
