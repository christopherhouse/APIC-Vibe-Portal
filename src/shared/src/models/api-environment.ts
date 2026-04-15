/**
 * An environment where APIs can be deployed (e.g., development, staging, production).
 */
export interface ApiEnvironment {
  id: string;
  name: string;
  title: string;
  description?: string;
  kind: EnvironmentKind;
}

/**
 * The kind of environment.
 */
export enum EnvironmentKind {
  Development = 'development',
  Staging = 'staging',
  Testing = 'testing',
  Production = 'production',
}
