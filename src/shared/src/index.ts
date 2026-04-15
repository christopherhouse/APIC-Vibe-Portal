// Enums
export { ApiLifecycle } from './enums/api-lifecycle.js';
export { ApiKind } from './enums/api-kind.js';
export { GovernanceStatus } from './enums/governance-status.js';

// Models
export type { ApiDefinition, ExternalDoc, Contact } from './models/api-definition.js';
export type { ApiVersion } from './models/api-version.js';
export type { ApiDeployment, DeploymentServer } from './models/api-deployment.js';
export type { ApiEnvironment } from './models/api-environment.js';
export { EnvironmentKind } from './models/api-environment.js';
export type {
  SearchResult,
  SearchFacets,
  SearchFacet,
  SearchFacetValue,
} from './models/search-result.js';
export type { ChatMessage, ChatSession, Citation, ChatRole } from './models/chat-message.js';
export type { User } from './models/user.js';
export type { PaginationParams, PaginationMeta, PaginatedResponse } from './models/pagination.js';

// DTOs
export type { ApiCatalogItem, ApiCatalogResponse } from './dto/api-catalog-response.js';
export { toApiCatalogItem } from './dto/api-catalog-response.js';
export type {
  ApiDetailResponse,
  GovernanceInfo,
  GovernanceRuleResult,
} from './dto/api-detail-response.js';
export type {
  SearchRequest,
  SearchFilters,
  SearchSortField,
  SearchSortOrder,
} from './dto/search-request.js';
export type { SearchResponse } from './dto/search-response.js';
export type { ChatRequest } from './dto/chat-request.js';
export type { ChatResponse } from './dto/chat-response.js';

// Errors
export { ErrorCode } from './errors/error-codes.js';
export { AppError } from './errors/app-error.js';
export type { ErrorResponse } from './errors/app-error.js';

// Utilities
export {
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
} from './utils/type-guards.js';
export {
  formatDate,
  formatRelativeTime,
  formatBytes,
  normalizeUrl,
  truncate,
} from './utils/formatters.js';

