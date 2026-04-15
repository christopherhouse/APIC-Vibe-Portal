/**
 * MSAL (Microsoft Authentication Library) configuration for Entra ID.
 *
 * Reads configuration from NEXT_PUBLIC_* environment variables.
 * These must be set in the deployment environment or `.env.local` for local development.
 */

import { type Configuration, LogLevel } from '@azure/msal-browser';

/**
 * MSAL configuration object.
 *
 * @see https://github.com/AzureAD/microsoft-authentication-library-for-js/blob/dev/lib/msal-browser/docs/configuration.md
 */
export const msalConfig: Configuration = {
  auth: {
    clientId: process.env.NEXT_PUBLIC_MSAL_CLIENT_ID ?? '',
    authority:
      process.env.NEXT_PUBLIC_MSAL_AUTHORITY ?? 'https://login.microsoftonline.com/common',
    redirectUri: process.env.NEXT_PUBLIC_MSAL_REDIRECT_URI ?? 'http://localhost:3000',
    postLogoutRedirectUri:
      process.env.NEXT_PUBLIC_MSAL_REDIRECT_URI ?? 'http://localhost:3000',
    navigateToLoginRequestUrl: true,
  },
  cache: {
    cacheLocation: 'sessionStorage',
    storeAuthStateInCookie: false,
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

/**
 * Scopes required to access the BFF API.
 * The scope should match the "Expose an API" scope on the BFF app registration.
 */
export const bffApiScope = process.env.NEXT_PUBLIC_BFF_API_SCOPE ?? '';

/**
 * Login request configuration — scopes requested during interactive sign-in.
 */
export const loginRequest = {
  scopes: bffApiScope ? [bffApiScope] : ['openid', 'profile', 'email'],
};
