import { ApiDefinition } from '../models/api-definition.js';
import { ApiVersion } from '../models/api-version.js';
import { ApiDeployment } from '../models/api-deployment.js';
import { ChatMessage } from '../models/chat-message.js';
import { SearchResult } from '../models/search-result.js';
import { PaginatedResponse } from '../models/pagination.js';
import { ErrorResponse } from '../errors/app-error.js';
import { ApiKind } from '../enums/api-kind.js';
import { ApiLifecycle } from '../enums/api-lifecycle.js';
import { GovernanceStatus } from '../enums/governance-status.js';
import { ErrorCode } from '../errors/error-codes.js';

function isNonNullObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function hasStringProp(obj: Record<string, unknown>, key: string): boolean {
  return typeof obj[key] === 'string';
}

function hasNumberProp(obj: Record<string, unknown>, key: string): boolean {
  return typeof obj[key] === 'number';
}

/**
 * Type guard for ApiDefinition.
 * Validates all required fields including enum values for kind and lifecycleStage.
 */
export function isApiDefinition(value: unknown): value is ApiDefinition {
  if (!isNonNullObject(value)) return false;
  return (
    hasStringProp(value, 'id') &&
    hasStringProp(value, 'name') &&
    hasStringProp(value, 'title') &&
    hasStringProp(value, 'description') &&
    isApiKind(value.kind) &&
    isApiLifecycle(value.lifecycleStage) &&
    Array.isArray(value.versions) &&
    Array.isArray(value.deployments) &&
    hasStringProp(value, 'createdAt') &&
    hasStringProp(value, 'updatedAt')
  );
}

/**
 * Type guard for ApiVersion.
 * Validates all required fields including enum value for lifecycleStage.
 */
export function isApiVersion(value: unknown): value is ApiVersion {
  if (!isNonNullObject(value)) return false;
  return (
    hasStringProp(value, 'id') &&
    hasStringProp(value, 'name') &&
    hasStringProp(value, 'title') &&
    isApiLifecycle(value.lifecycleStage) &&
    hasStringProp(value, 'createdAt') &&
    hasStringProp(value, 'updatedAt')
  );
}

/**
 * Type guard for ApiDeployment.
 * Validates all required fields including server.runtimeUri and timestamps.
 */
export function isApiDeployment(value: unknown): value is ApiDeployment {
  if (!isNonNullObject(value)) return false;
  if (
    !hasStringProp(value, 'id') ||
    !hasStringProp(value, 'title') ||
    !isNonNullObject(value.environment) ||
    !isNonNullObject(value.server) ||
    !hasStringProp(value, 'createdAt') ||
    !hasStringProp(value, 'updatedAt')
  ) {
    return false;
  }
  const server = value.server as Record<string, unknown>;
  return Array.isArray(server.runtimeUri);
}

/**
 * Type guard for ChatMessage.
 */
export function isChatMessage(value: unknown): value is ChatMessage {
  if (!isNonNullObject(value)) return false;
  return (
    hasStringProp(value, 'id') &&
    hasStringProp(value, 'role') &&
    ['user', 'assistant', 'system'].includes(value.role as string) &&
    hasStringProp(value, 'content') &&
    hasStringProp(value, 'timestamp')
  );
}

/**
 * Type guard for SearchResult.
 * Validates required fields including queryDuration, and optionally validates items
 * with the provided item guard.
 */
export function isSearchResult<T>(
  value: unknown,
  itemGuard?: (item: unknown) => item is T
): value is SearchResult<T> {
  if (!isNonNullObject(value)) return false;
  if (
    !Array.isArray(value.items) ||
    !hasNumberProp(value, 'totalCount') ||
    !hasNumberProp(value, 'queryDuration')
  ) {
    return false;
  }
  if (itemGuard) {
    return (value.items as unknown[]).every(itemGuard);
  }
  return true;
}

/**
 * Type guard for PaginatedResponse.
 * Validates required pagination properties (page, pageSize, totalCount, totalPages),
 * and optionally validates items with the provided item guard.
 */
export function isPaginatedResponse<T>(
  value: unknown,
  itemGuard?: (item: unknown) => item is T
): value is PaginatedResponse<T> {
  if (!isNonNullObject(value)) return false;
  if (!Array.isArray(value.items) || !isNonNullObject(value.pagination)) {
    return false;
  }
  const pagination = value.pagination as Record<string, unknown>;
  if (
    !hasNumberProp(pagination, 'page') ||
    !hasNumberProp(pagination, 'pageSize') ||
    !hasNumberProp(pagination, 'totalCount') ||
    !hasNumberProp(pagination, 'totalPages')
  ) {
    return false;
  }
  if (itemGuard) {
    return (value.items as unknown[]).every(itemGuard);
  }
  return true;
}

/**
 * Type guard for ErrorResponse.
 * Validates that code is a valid ErrorCode enum value.
 */
export function isErrorResponse(value: unknown): value is ErrorResponse {
  if (!isNonNullObject(value)) return false;
  if (!isErrorCode(value.code) || !hasStringProp(value, 'message')) {
    return false;
  }
  if (value.details !== undefined && !isNonNullObject(value.details)) {
    return false;
  }
  return true;
}

/**
 * Type guard for ApiKind enum value.
 */
export function isApiKind(value: unknown): value is ApiKind {
  return Object.values(ApiKind).includes(value as ApiKind);
}

/**
 * Type guard for ApiLifecycle enum value.
 */
export function isApiLifecycle(value: unknown): value is ApiLifecycle {
  return Object.values(ApiLifecycle).includes(value as ApiLifecycle);
}

/**
 * Type guard for GovernanceStatus enum value.
 */
export function isGovernanceStatus(value: unknown): value is GovernanceStatus {
  return Object.values(GovernanceStatus).includes(value as GovernanceStatus);
}

/**
 * Type guard for ErrorCode enum value.
 */
export function isErrorCode(value: unknown): value is ErrorCode {
  return Object.values(ErrorCode).includes(value as ErrorCode);
}
