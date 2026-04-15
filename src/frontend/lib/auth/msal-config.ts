/**
 * MSAL (Microsoft Authentication Library) configuration for Entra ID.
 *
 * Uses environment variables prefixed with NEXT_PUBLIC_ so they are
 * available in the browser bundle.
 */

import { type Configuration, LogLevel } from '@azure/msal-browser';

/** MSAL configuration for the frontend SPA. */
export const msalConfig: Configuration = {
  auth: {
    clientId: process.env.NEXT_PUBLIC_MSAL_CLIENT_ID ?? '',
    authority:
      process.env.NEXT_PUBLIC_MSAL_AUTHORITY ??
      'https://login.microsoftonline.com/common',
    redirectUri: process.env.NEXT_PUBLIC_MSAL_REDIRECT_URI ?? 'http://localhost:3000',
    postLogoutRedirectUri: process.env.NEXT_PUBLIC_MSAL_REDIRECT_URI ?? 'http://localhost:3000',
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

/** The scope to request when acquiring tokens for the BFF API. */
export const bffApiScope =
  process.env.NEXT_PUBLIC_BFF_API_SCOPE ?? 'api://bff/.default';

/** Login request configuration. */
export const loginRequest = {
  scopes: [bffApiScope],
};

/** Token request for acquiring access tokens silently. */
export const tokenRequest = {
  scopes: [bffApiScope],
};
