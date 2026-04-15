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

/**
 * Type guard for ApiDefinition.
 */
export function isApiDefinition(value: unknown): value is ApiDefinition {
  if (!isNonNullObject(value)) return false;
  return (
    hasStringProp(value, 'id') &&
    hasStringProp(value, 'name') &&
    hasStringProp(value, 'title') &&
    hasStringProp(value, 'kind') &&
    hasStringProp(value, 'lifecycleStage') &&
    Array.isArray(value.versions) &&
    Array.isArray(value.deployments)
  );
}

/**
 * Type guard for ApiVersion.
 */
export function isApiVersion(value: unknown): value is ApiVersion {
  if (!isNonNullObject(value)) return false;
  return (
    hasStringProp(value, 'id') &&
    hasStringProp(value, 'name') &&
    hasStringProp(value, 'title') &&
    hasStringProp(value, 'lifecycleStage')
  );
}

/**
 * Type guard for ApiDeployment.
 */
export function isApiDeployment(value: unknown): value is ApiDeployment {
  if (!isNonNullObject(value)) return false;
  return (
    hasStringProp(value, 'id') &&
    hasStringProp(value, 'title') &&
    isNonNullObject(value.environment) &&
    isNonNullObject(value.server)
  );
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
 */
export function isSearchResult<T>(
  value: unknown,
  _itemGuard?: (item: unknown) => item is T
): value is SearchResult<T> {
  if (!isNonNullObject(value)) return false;
  return Array.isArray(value.items) && typeof value.totalCount === 'number';
}

/**
 * Type guard for PaginatedResponse.
 */
export function isPaginatedResponse<T>(
  value: unknown,
  _itemGuard?: (item: unknown) => item is T
): value is PaginatedResponse<T> {
  if (!isNonNullObject(value)) return false;
  return Array.isArray(value.items) && isNonNullObject(value.pagination);
}

/**
 * Type guard for ErrorResponse.
 */
export function isErrorResponse(value: unknown): value is ErrorResponse {
  if (!isNonNullObject(value)) return false;
  return hasStringProp(value, 'code') && hasStringProp(value, 'message');
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
