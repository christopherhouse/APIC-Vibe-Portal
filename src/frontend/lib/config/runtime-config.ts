/**
 * Runtime configuration client.
 *
 * Fetches environment-specific configuration from the server at app startup.
 * This allows the same Docker image to run in dev, staging, and prod with
 * different configurations injected at runtime.
 */

import type { RuntimeConfig } from '@/app/api/config/route';

let cachedConfig: RuntimeConfig | null = null;
let configPromise: Promise<RuntimeConfig> | null = null;

/**
 * Fetch runtime configuration from the server.
 *
 * The config is cached in memory after the first fetch.
 * If multiple components call this simultaneously during app startup,
 * they all receive the same promise (no duplicate requests).
 */
export async function getRuntimeConfig(): Promise<RuntimeConfig> {
  // Return cached config if available
  if (cachedConfig) {
    return cachedConfig;
  }

  // If a fetch is already in progress, return that promise
  if (configPromise) {
    return configPromise;
  }

  // Start a new fetch
  configPromise = fetch('/api/config', {
    // Respect the server's cache headers
    cache: 'default',
  })
    .then((res) => {
      if (!res.ok) {
        throw new Error(`Failed to fetch runtime config: ${res.status} ${res.statusText}`);
      }
      return res.json() as Promise<RuntimeConfig>;
    })
    .then((config) => {
      cachedConfig = config;
      return config;
    })
    .catch((error) => {
      // Clear the promise so the next call retries
      configPromise = null;
      throw error;
    });

  return configPromise;
}

/**
 * Clear the cached config (useful for testing).
 */
export function clearConfigCache(): void {
  cachedConfig = null;
  configPromise = null;
}
