'use client';

/**
 * Custom authentication hook wrapping MSAL React.
 *
 * Provides a simple API for components to:
 * - Check authentication status
 * - Get user information
 * - Trigger login/logout
 * - Acquire access tokens for the BFF API
 */

import { useCallback, useMemo } from 'react';

import { InteractionStatus } from '@azure/msal-browser';
import { useIsAuthenticated, useMsal } from '@azure/msal-react';

import { loginRequest, tokenRequest } from './msal-config';

export interface AuthUser {
  name: string;
  email: string;
  oid: string;
  roles: string[];
}

export interface UseAuthResult {
  /** Whether the user is authenticated. */
  isAuthenticated: boolean;
  /** Whether an authentication interaction is in progress. */
  isLoading: boolean;
  /** The current user info, or null if not authenticated. */
  user: AuthUser | null;
  /** Trigger login via redirect. */
  login: () => Promise<void>;
  /** Trigger logout via redirect. */
  logout: () => Promise<void>;
  /** Acquire an access token for the BFF API. */
  getToken: () => Promise<string | null>;
}

/**
 * Hook providing authentication state and operations.
 */
export function useAuth(): UseAuthResult {
  const { instance, accounts, inProgress } = useMsal();
  const isAuthenticated = useIsAuthenticated();

  const isLoading = inProgress !== InteractionStatus.None;

  const user: AuthUser | null = useMemo(() => {
    if (!isAuthenticated || accounts.length === 0) return null;

    const account = accounts[0];
    const claims = account.idTokenClaims as Record<string, unknown> | undefined;

    return {
      name: account.name ?? '',
      email: account.username ?? '',
      oid: (claims?.oid as string) ?? account.localAccountId ?? '',
      roles: (claims?.roles as string[]) ?? [],
    };
  }, [isAuthenticated, accounts]);

  const login = useCallback(async () => {
    try {
      await instance.loginRedirect(loginRequest);
    } catch (error) {
      console.error('Login failed:', error);
    }
  }, [instance]);

  const logout = useCallback(async () => {
    try {
      await instance.logoutRedirect({
        postLogoutRedirectUri: '/',
      });
    } catch (error) {
      console.error('Logout failed:', error);
    }
  }, [instance]);

  const getToken = useCallback(async (): Promise<string | null> => {
    if (!isAuthenticated || accounts.length === 0) return null;

    try {
      const response = await instance.acquireTokenSilent({
        ...tokenRequest,
        account: accounts[0],
      });
      return response.accessToken;
    } catch {
      // Silent token acquisition failed — try interactive
      try {
        await instance.acquireTokenRedirect(tokenRequest);
        return null; // Will redirect, so we won't return
      } catch (interactiveError) {
        console.error('Token acquisition failed:', interactiveError);
        return null;
      }
    }
  }, [instance, accounts, isAuthenticated]);

  return {
    isAuthenticated,
    isLoading,
    user,
    login,
    logout,
    getToken,
  };
}
