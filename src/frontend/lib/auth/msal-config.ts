/**
 * MSAL (Microsoft Authentication Library) configuration for Entra ID.
 *
 * Reads configuration from NEXT_PUBLIC_* environment variables.
 * These must be set in the deployment environment or `.env.local` for local development.
 */

import { type Configuration, LogLevel } from '@azure/msal-browser';

/**
 * Validates that required MSAL environment variables are set.
 * Logs clear warnings in development so misconfiguration is obvious.
 */
function validateMsalEnv(): void {
  if (typeof window === 'undefined') return; // skip during SSR / build

  const missing: string[] = [];
  if (!process.env.NEXT_PUBLIC_MSAL_CLIENT_ID) missing.push('NEXT_PUBLIC_MSAL_CLIENT_ID');
  if (!process.env.NEXT_PUBLIC_MSAL_AUTHORITY) missing.push('NEXT_PUBLIC_MSAL_AUTHORITY');

  if (missing.length > 0) {
    console.error(
      `[MSAL Config] Missing required environment variable(s): ${missing.join(', ')}. ` +
        'Entra ID authentication will not work. ' +
        'Copy .env.example to .env.local and fill in the values for your Entra ID app registration.'
    );
  }
}

validateMsalEnv();

/**
 * MSAL configuration object.
 *
 * @see https://github.com/AzureAD/microsoft-authentication-library-for-js/blob/dev/lib/msal-browser/docs/configuration.md
 */
export const msalConfig: Configuration = {
  auth: {
    clientId: process.env.NEXT_PUBLIC_MSAL_CLIENT_ID ?? '',
    authority: process.env.NEXT_PUBLIC_MSAL_AUTHORITY ?? 'https://login.microsoftonline.com/common',
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
