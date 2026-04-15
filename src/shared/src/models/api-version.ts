import { ApiLifecycle } from '../enums/api-lifecycle.js';

/**
 * A specific version of an API.
 */
export interface ApiVersion {
  id: string;
  name: string;
  title: string;
  lifecycleStage: ApiLifecycle;
  createdAt: string;
  updatedAt: string;
}
