/**
 * Tests for the catalog detail API client.
 */

import {
  fetchApiDetail,
  fetchApiVersions,
  fetchApiDeployments,
  fetchApiDefinition,
} from '../catalog-detail-api';

// Mock the api-client module
const mockGet = jest.fn();
jest.mock('@/lib/api-client', () => ({
  apiClient: {
    get: (...args: unknown[]) => mockGet(...args),
  },
}));

describe('catalog-detail-api', () => {
  beforeEach(() => {
    mockGet.mockClear();
  });

  describe('fetchApiDetail', () => {
    it('fetches API detail and returns data', async () => {
      const mockData = {
        id: 'api-1',
        name: 'petstore',
        title: 'Petstore API',
      };
      mockGet.mockResolvedValue({ data: mockData });

      const result = await fetchApiDetail('api-1');
      expect(mockGet).toHaveBeenCalledWith('/api/catalog/api-1');
      expect(result).toEqual(mockData);
    });

    it('throws on error', async () => {
      mockGet.mockRejectedValue(new Error('Not found'));
      await expect(fetchApiDetail('bad-id')).rejects.toThrow('Not found');
    });
  });

  describe('fetchApiVersions', () => {
    it('fetches versions for an API', async () => {
      const mockVersions = [{ id: 'v1', title: 'Version 1' }];
      mockGet.mockResolvedValue({ data: mockVersions });

      const result = await fetchApiVersions('api-1');
      expect(mockGet).toHaveBeenCalledWith('/api/catalog/api-1/versions');
      expect(result).toEqual(mockVersions);
    });
  });

  describe('fetchApiDeployments', () => {
    it('fetches deployments for an API', async () => {
      const mockDeployments = [{ id: 'dep-1', title: 'Prod' }];
      mockGet.mockResolvedValue({ data: mockDeployments });

      const result = await fetchApiDeployments('api-1');
      expect(mockGet).toHaveBeenCalledWith('/api/catalog/api-1/deployments');
      expect(result).toEqual(mockDeployments);
    });
  });

  describe('fetchApiDefinition', () => {
    it('fetches definition for a version and extracts content', async () => {
      const mockSpecContent = '{"openapi": "3.0.0"}';
      mockGet.mockResolvedValue({
        data: {
          id: 'def-1',
          name: 'openapi',
          title: 'OpenAPI',
          specificationType: 'openapi',
          specificationVersion: '3.0.0',
          content: mockSpecContent,
        },
      });

      const result = await fetchApiDefinition('api-1', 'v1');
      expect(mockGet).toHaveBeenCalledWith('/api/catalog/api-1/versions/v1/definition');
      expect(result).toEqual(mockSpecContent);
    });

    it('returns null when content is null', async () => {
      mockGet.mockResolvedValue({
        data: {
          id: 'def-1',
          name: 'openapi',
          title: 'OpenAPI',
          content: null,
        },
      });

      const result = await fetchApiDefinition('api-1', 'v1');
      expect(result).toBeNull();
    });
  });
});
