import { AppError } from '../../src/errors/app-error.js';
import { ErrorCode } from '../../src/errors/error-codes.js';
import { toApiCatalogItem } from '../../src/dto/api-catalog-response.js';
import { ApiKind } from '../../src/enums/api-kind.js';
import { ApiLifecycle } from '../../src/enums/api-lifecycle.js';
import type { ApiDefinition } from '../../src/models/api-definition.js';

describe('AppError', () => {
  it('creates an error with code and message', () => {
    const err = new AppError(ErrorCode.NotFound, 'Resource not found', 404);
    expect(err.code).toBe(ErrorCode.NotFound);
    expect(err.message).toBe('Resource not found');
    expect(err.statusCode).toBe(404);
    expect(err.name).toBe('AppError');
    expect(err).toBeInstanceOf(Error);
  });

  it('defaults statusCode to 500', () => {
    const err = new AppError(ErrorCode.InternalError, 'Something went wrong');
    expect(err.statusCode).toBe(500);
  });

  it('serializes to JSON', () => {
    const err = new AppError(ErrorCode.ValidationError, 'Invalid field', 400, {
      field: 'name',
    });
    const json = err.toJSON();
    expect(json).toEqual({
      code: 'VALIDATION_ERROR',
      message: 'Invalid field',
      details: { field: 'name' },
    });
  });

  it('omits details from JSON when undefined', () => {
    const err = new AppError(ErrorCode.NotFound, 'Not found', 404);
    const json = err.toJSON();
    expect(json).toEqual({
      code: 'NOT_FOUND',
      message: 'Not found',
    });
    expect('details' in json).toBe(false);
  });
});

describe('toApiCatalogItem', () => {
  it('transforms an ApiDefinition to a catalog item', () => {
    const api: ApiDefinition = {
      id: '1',
      name: 'my-api',
      title: 'My API',
      description: 'A test API',
      kind: ApiKind.REST,
      lifecycleStage: ApiLifecycle.Production,
      versions: [
        {
          id: 'v1',
          name: 'v1.0',
          title: 'V1',
          lifecycleStage: ApiLifecycle.Production,
          createdAt: '2024-01-01',
          updatedAt: '2024-01-01',
        },
      ],
      deployments: [],
      createdAt: '2024-01-01',
      updatedAt: '2024-06-15',
    };

    const item = toApiCatalogItem(api);
    expect(item).toEqual({
      id: '1',
      name: 'my-api',
      title: 'My API',
      description: 'A test API',
      kind: 'rest',
      lifecycleStage: 'production',
      versionCount: 1,
      deploymentCount: 0,
      updatedAt: '2024-06-15',
    });
  });
});
