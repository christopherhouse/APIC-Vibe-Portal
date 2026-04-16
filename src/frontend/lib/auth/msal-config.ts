/**
 * MSAL (Microsoft Authentication Library) configuration for Entra ID.
 *
 * Configuration is now loaded from the server at runtime via `/api/config`,
 * allowing the same Docker image to be deployed across dev, staging, and prod.
 */

import { type Configuration, LogLevel } from '@azure/msal-browser';
import type { RuntimeConfig } from '@/app/api/config/route';

/**
 * Build MSAL configuration from runtime config.
 *
 * @param config Runtime configuration fetched from `/api/config`
 */
export function buildMsalConfig(config: RuntimeConfig): Configuration {
  return {
    auth: {
      clientId: config.msal.clientId,
      authority: config.msal.authority,
      redirectUri: config.msal.redirectUri,
      postLogoutRedirectUri: config.msal.redirectUri,
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
 * @param config Runtime configuration fetched from `/api/config`
 */
export function buildLoginRequest(config: RuntimeConfig) {
  const scopes = config.bffApiScope ? [config.bffApiScope] : ['openid', 'profile', 'email'];
  return { scopes };
}
