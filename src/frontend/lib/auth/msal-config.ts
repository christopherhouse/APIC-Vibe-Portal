/**
 * MSAL (Microsoft Authentication Library) configuration for Entra ID.
 *
 * Fetches configuration from the runtime API endpoint at application startup.
 * This allows the same Docker image to be deployed across environments with
 * different configuration values injected at runtime via Container App env vars.
 */

import { type Configuration, LogLevel } from '@azure/msal-browser';

export interface MsalConfig {
  clientId: string;
  authority: string;
  redirectUri: string;
  bffApiScope: string;
}

/**
 * Fetch MSAL configuration from the server at runtime.
 * This is called once during application initialization.
 */
export async function fetchMsalConfig(): Promise<MsalConfig> {
  try {
    const response = await fetch('/api/config/msal');
    if (!response.ok) {
      throw new Error(`Failed to fetch MSAL config: ${response.status} ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.error('[MSAL Config] Failed to fetch runtime configuration:', error);
    throw error;
  }
}

/**
 * Build MSAL browser configuration from runtime config.
 *
 * @param config - Runtime MSAL configuration fetched from API
 * @returns MSAL browser configuration object
 * @see https://github.com/AzureAD/microsoft-authentication-library-for-js/blob/dev/lib/msal-browser/docs/configuration.md
 */
export function buildMsalConfig(config: MsalConfig): Configuration {
  return {
    auth: {
      clientId: config.clientId,
      authority: config.authority,
      redirectUri: config.redirectUri,
      postLogoutRedirectUri: config.redirectUri,
    },
    cache: {
      cacheLocation: 'sessionStorage',
    },
    system: {
      loggerOptions: {
        logLevel: LogLevel.Warning,
        loggerCallback: (level, message, containsPii) => {
          if (containsPii) return;
          switch (level) {
            case LogLevel.Error:
              console.error(message);
              break;
            case LogLevel.Warning:
              console.warn(message);
              break;
            default:
              break;
          }
        },
      },
    },
  };
}

/**
 * Build login request configuration from runtime config.
 *
 * @param config - Runtime MSAL configuration fetched from API
 * @returns Login request with scopes
 */
export function buildLoginRequest(config: MsalConfig) {
  return {
    scopes: config.bffApiScope ? [config.bffApiScope] : ['openid', 'profile', 'email'],
  };
}
