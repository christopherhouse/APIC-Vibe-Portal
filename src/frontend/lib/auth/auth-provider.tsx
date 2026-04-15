'use client';

/**
 * MSAL React provider wrapper for the application.
 *
 * Initialises a PublicClientApplication instance and wraps children
 * with the MsalProvider from @azure/msal-react.
 */

import { type ReactNode, useEffect, useRef, useState } from 'react';

import { PublicClientApplication } from '@azure/msal-browser';
import { MsalProvider } from '@azure/msal-react';

import { msalConfig } from './msal-config';

interface AuthProviderProps {
  children: ReactNode;
}

/**
 * Provides MSAL authentication context to the component tree.
 *
 * Creates a single PublicClientApplication instance and handles
 * the auth redirect promise on mount.
 */
export default function AuthProvider({ children }: AuthProviderProps) {
  const msalInstanceRef = useRef<PublicClientApplication | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);

  if (!msalInstanceRef.current) {
    msalInstanceRef.current = new PublicClientApplication(msalConfig);
  }

  useEffect(() => {
    const instance = msalInstanceRef.current;
    if (!instance) return;

    instance
      .initialize()
      .then(() => {
        // Handle redirect response after login
        return instance.handleRedirectPromise();
      })
      .then((response) => {
        if (response?.account) {
          instance.setActiveAccount(response.account);
        } else {
          // Set active account if one already exists
          const accounts = instance.getAllAccounts();
          if (accounts.length > 0) {
            instance.setActiveAccount(accounts[0]);
          }
        }
        setIsInitialized(true);
      })
      .catch((error) => {
        console.error('MSAL initialization error:', error);
        setIsInitialized(true);
      });
  }, []);

  if (!isInitialized || !msalInstanceRef.current) {
    return null;
  }

  return <MsalProvider instance={msalInstanceRef.current}>{children}</MsalProvider>;
}
