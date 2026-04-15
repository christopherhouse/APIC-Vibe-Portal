import {
  isApiDefinition,
  isApiVersion,
  isApiDeployment,
  isChatMessage,
  isSearchResult,
  isPaginatedResponse,
  isErrorResponse,
  isApiKind,
  isApiLifecycle,
  isGovernanceStatus,
  isErrorCode,
} from '../../src/utils/type-guards.js';
import { ApiKind } from '../../src/enums/api-kind.js';
import { ApiLifecycle } from '../../src/enums/api-lifecycle.js';
import { GovernanceStatus } from '../../src/enums/governance-status.js';
import { ErrorCode } from '../../src/errors/error-codes.js';

describe('type-guards', () => {
  describe('isApiDefinition', () => {
    const validApiDef = {
      id: '1',
      name: 'my-api',
      title: 'My API',
      description: 'desc',
      kind: 'rest',
      lifecycleStage: 'production',
      versions: [],
      deployments: [],
      createdAt: '2024-01-01',
      updatedAt: '2024-01-01',
    };

    it('returns true for a valid ApiDefinition', () => {
      expect(isApiDefinition(validApiDef)).toBe(true);
    });

    it('returns false for null', () => {
      expect(isApiDefinition(null)).toBe(false);
    });

    it('returns false for undefined', () => {
      expect(isApiDefinition(undefined)).toBe(false);
    });

    it('returns false for a string', () => {
      expect(isApiDefinition('not an object')).toBe(false);
    });

    it('returns false for an array', () => {
      expect(isApiDefinition([])).toBe(false);
    });

    it('returns false when missing required fields', () => {
      expect(isApiDefinition({ id: '1', name: 'test' })).toBe(false);
    });

    it('returns false when versions is not an array', () => {
      expect(isApiDefinition({ ...validApiDef, versions: 'not-array' })).toBe(false);
    });
  });

  describe('isApiVersion', () => {
    const validVersion = {
      id: 'v1',
      name: 'v1.0',
      title: 'Version 1',
      lifecycleStage: 'production',
      createdAt: '2024-01-01',
      updatedAt: '2024-01-01',
    };

    it('returns true for a valid ApiVersion', () => {
      expect(isApiVersion(validVersion)).toBe(true);
    });

    it('returns false for null', () => {
      expect(isApiVersion(null)).toBe(false);
    });

    it('returns false for incomplete object', () => {
      expect(isApiVersion({ id: 'v1' })).toBe(false);
    });
  });

  describe('isApiDeployment', () => {
    const validDeployment = {
      id: 'd1',
      title: 'Prod Deployment',
      environment: { id: 'e1', name: 'prod', title: 'Production', kind: 'production' },
      server: { runtimeUri: ['https://api.example.com'] },
      createdAt: '2024-01-01',
      updatedAt: '2024-01-01',
    };

    it('returns true for a valid ApiDeployment', () => {
      expect(isApiDeployment(validDeployment)).toBe(true);
    });

    it('returns false for null', () => {
      expect(isApiDeployment(null)).toBe(false);
    });

    it('returns false when environment is missing', () => {
      expect(isApiDeployment({ id: 'd1', title: 'x', server: {} })).toBe(false);
    });

    it('returns false when server is a string', () => {
      expect(
        isApiDeployment({ id: 'd1', title: 'x', environment: {}, server: 'not-object' })
      ).toBe(false);
    });
  });

  describe('isChatMessage', () => {
    const validMsg = {
      id: 'm1',
      role: 'user',
      content: 'Hello',
      timestamp: '2024-01-01T00:00:00Z',
    };

    it('returns true for a valid ChatMessage', () => {
      expect(isChatMessage(validMsg)).toBe(true);
    });

    it('returns true for assistant role', () => {
      expect(isChatMessage({ ...validMsg, role: 'assistant' })).toBe(true);
    });

    it('returns true for system role', () => {
      expect(isChatMessage({ ...validMsg, role: 'system' })).toBe(true);
    });

    it('returns false for invalid role', () => {
      expect(isChatMessage({ ...validMsg, role: 'invalid' })).toBe(false);
    });

    it('returns false for null', () => {
      expect(isChatMessage(null)).toBe(false);
    });
  });

  describe('isSearchResult', () => {
    it('returns true for a valid SearchResult', () => {
      expect(isSearchResult({ items: [], totalCount: 0, queryDuration: 10 })).toBe(true);
    });

    it('returns false when items is not an array', () => {
      expect(isSearchResult({ items: 'not-array', totalCount: 0 })).toBe(false);
    });

    it('returns false when totalCount is missing', () => {
      expect(isSearchResult({ items: [] })).toBe(false);
    });

    it('returns false for null', () => {
      expect(isSearchResult(null)).toBe(false);
    });
  });

  describe('isPaginatedResponse', () => {
    it('returns true for a valid PaginatedResponse', () => {
      expect(
        isPaginatedResponse({
          items: [],
          pagination: { page: 1, pageSize: 10, totalCount: 0, totalPages: 0 },
        })
      ).toBe(true);
    });

    it('returns false when pagination is missing', () => {
      expect(isPaginatedResponse({ items: [] })).toBe(false);
    });

    it('returns false for null', () => {
      expect(isPaginatedResponse(null)).toBe(false);
    });
  });

  describe('isErrorResponse', () => {
    it('returns true for a valid ErrorResponse', () => {
      expect(isErrorResponse({ code: 'NOT_FOUND', message: 'Not found' })).toBe(true);
    });

    it('returns false when code is missing', () => {
      expect(isErrorResponse({ message: 'Not found' })).toBe(false);
    });

    it('returns false for null', () => {
      expect(isErrorResponse(null)).toBe(false);
    });
  });

  describe('enum type guards', () => {
    describe('isApiKind', () => {
      it('returns true for valid ApiKind values', () => {
        expect(isApiKind(ApiKind.REST)).toBe(true);
        expect(isApiKind('rest')).toBe(true);
        expect(isApiKind('graphql')).toBe(true);
      });

      it('returns false for invalid values', () => {
        expect(isApiKind('invalid')).toBe(false);
        expect(isApiKind(42)).toBe(false);
        expect(isApiKind(null)).toBe(false);
      });
    });

    describe('isApiLifecycle', () => {
      it('returns true for valid ApiLifecycle values', () => {
        expect(isApiLifecycle(ApiLifecycle.Production)).toBe(true);
        expect(isApiLifecycle('design')).toBe(true);
      });

      it('returns false for invalid values', () => {
        expect(isApiLifecycle('invalid')).toBe(false);
      });
    });

    describe('isGovernanceStatus', () => {
      it('returns true for valid GovernanceStatus values', () => {
        expect(isGovernanceStatus(GovernanceStatus.Compliant)).toBe(true);
        expect(isGovernanceStatus('non-compliant')).toBe(true);
      });

      it('returns false for invalid values', () => {
        expect(isGovernanceStatus('invalid')).toBe(false);
      });
    });

    describe('isErrorCode', () => {
      it('returns true for valid ErrorCode values', () => {
        expect(isErrorCode(ErrorCode.NotFound)).toBe(true);
        expect(isErrorCode('NOT_FOUND')).toBe(true);
      });

      it('returns false for invalid values', () => {
        expect(isErrorCode('DOES_NOT_EXIST')).toBe(false);
      });
    });
  });
});
