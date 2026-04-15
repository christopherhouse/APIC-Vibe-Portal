import { ApiKind } from '../enums/api-kind.js';
import { ApiLifecycle } from '../enums/api-lifecycle.js';
import { ApiVersion } from './api-version.js';
import { ApiDeployment } from './api-deployment.js';

/**
 * External documentation link for an API.
 */
export interface ExternalDoc {
  title: string;
  url: string;
  description?: string;
}

/**
 * Contact information for an API.
 */
export interface Contact {
  name: string;
  email?: string;
  url?: string;
}

/**
 * Core API definition model, mirroring Azure API Center's API entity.
 * This is the canonical reference for the BFF's corresponding Pydantic model.
 */
export interface ApiDefinition {
  id: string;
  name: string;
  title: string;
  description: string;
  kind: ApiKind;
  lifecycleStage: ApiLifecycle;
  termsOfService?: string;
  license?: string;
  externalDocs?: ExternalDoc[];
  contacts?: Contact[];
  customProperties?: Record<string, unknown>;
  versions: ApiVersion[];
  deployments: ApiDeployment[];
  createdAt: string;
  updatedAt: string;
}
