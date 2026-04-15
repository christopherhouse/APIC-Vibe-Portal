'use client';

/**
 * Custom authentication hook that wraps MSAL React primitives.
 *
 * Exposes a simple API: `isAuthenticated`, `user`, `login`, `logout`, `getToken`.
 */

import { useCallback } from 'react';
import { useMsal, useIsAuthenticated } from '@azure/msal-react';
import { InteractionRequiredAuthError } from '@azure/msal-browser';
import { loginRequest, bffApiScope } from './msal-config';

export interface AuthUser {
  name: string;
  email: string;
  id: string;
  roles: string[];
}

export interface UseAuthReturn {
  /** Whether the user is currently authenticated. */
  isAuthenticated: boolean;
  /** Parsed user profile from the active account, or `null`. */
  user: AuthUser | null;
  /** Initiate an interactive login redirect. */
  login: () => Promise<void>;
  /** Log out the current user via redirect. */
  logout: () => Promise<void>;
  /** Silently acquire an access token for the BFF API (falls back to interactive). */
  getToken: () => Promise<string | null>;
  /** Whether MSAL is processing an interaction (login/logout redirect). */
  isLoading: boolean;
}

/**
 * Hook that provides authentication state and actions.
 */
export function useAuth(): UseAuthReturn {
  const { instance, inProgress } = useMsal();
  const isAuthenticated = useIsAuthenticated();

  const user: AuthUser | null = (() => {
    const account = instance.getActiveAccount();
    if (!account) return null;
    return {
      name: account.name ?? '',
      email: account.username ?? '',
      id: account.localAccountId ?? '',
      roles: (account.idTokenClaims?.roles as string[] | undefined) ?? [],
    };
  })();

  const login = useCallback(async () => {
    await instance.loginRedirect(loginRequest);
  }, [instance]);

  const logout = useCallback(async () => {
    await instance.logoutRedirect({
      postLogoutRedirectUri: '/',
    });
  }, [instance]);

  const getToken = useCallback(async (): Promise<string | null> => {
    const account = instance.getActiveAccount();
    if (!account) return null;

    const tokenRequest = {
      scopes: bffApiScope ? [bffApiScope] : ['openid', 'profile', 'email'],
      account,
    };

    try {
      const result = await instance.acquireTokenSilent(tokenRequest);
      return result.accessToken;
    } catch (error) {
      if (error instanceof InteractionRequiredAuthError) {
        // Silent token acquisition failed; fall back to interactive
        await instance.acquireTokenRedirect(tokenRequest);
        return null;
      }
      console.error('Token acquisition failed:', error);
      return null;
    }
  }, [instance]);

  return {
    isAuthenticated,
    user,
    login,
    logout,
    getToken,
    isLoading: inProgress !== 'none',
  };
}
