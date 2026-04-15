/**
 * API lifecycle stages as defined by Azure API Center.
 * Represents the current stage of an API in its lifecycle.
 */
export enum ApiLifecycle {
  Design = 'design',
  Development = 'development',
  Testing = 'testing',
  Preview = 'preview',
  Production = 'production',
  Deprecated = 'deprecated',
  Retired = 'retired',
}
