import { ApiEnvironment } from './api-environment.js';

/**
 * Deployment information for an API version in a specific environment.
 */
export interface ApiDeployment {
  id: string;
  title: string;
  description?: string;
  environment: ApiEnvironment;
  server: DeploymentServer;
  createdAt: string;
  updatedAt: string;
}

/**
 * Server information for a deployed API.
 */
export interface DeploymentServer {
  runtimeUri: string[];
}
