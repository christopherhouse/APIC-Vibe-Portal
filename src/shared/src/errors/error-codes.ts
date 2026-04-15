/**
 * Standardized error codes for the application.
 */
export enum ErrorCode {
  // Client errors
  BadRequest = 'BAD_REQUEST',
  Unauthorized = 'UNAUTHORIZED',
  Forbidden = 'FORBIDDEN',
  NotFound = 'NOT_FOUND',
  Conflict = 'CONFLICT',
  ValidationError = 'VALIDATION_ERROR',

  // Server errors
  InternalError = 'INTERNAL_ERROR',
  ServiceUnavailable = 'SERVICE_UNAVAILABLE',
  GatewayTimeout = 'GATEWAY_TIMEOUT',

  // Domain-specific errors
  ApiNotFound = 'API_NOT_FOUND',
  VersionNotFound = 'VERSION_NOT_FOUND',
  SearchFailed = 'SEARCH_FAILED',
  ChatSessionNotFound = 'CHAT_SESSION_NOT_FOUND',
  ChatServiceError = 'CHAT_SERVICE_ERROR',
  GovernanceEvaluationFailed = 'GOVERNANCE_EVALUATION_FAILED',
}
