'use client';

/**
 * MSAL authentication provider that wraps the application.
 *
 * Initialises a `PublicClientApplication` singleton and provides it
 * to the React tree via `MsalProvider`.
 */

import React, { useEffect, useState } from 'react';
import {
  PublicClientApplication,
  EventType,
  type EventMessage,
  type AuthenticationResult,
} from '@azure/msal-browser';
import { MsalProvider } from '@azure/msal-react';
import { msalConfig } from './msal-config';

let msalInstance: PublicClientApplication | null = null;

/**
 * Get (or create) the singleton MSAL PublicClientApplication instance.
 */
export function getMsalInstance(): PublicClientApplication {
  if (!msalInstance) {
    msalInstance = new PublicClientApplication(msalConfig);
  }
  return msalInstance;
}

/**
 * AuthProvider initialises MSAL and wraps the React tree in `MsalProvider`.
 *
 * It waits for `msalInstance.initialize()` to complete before rendering children.
 */
export default function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isInitialized, setIsInitialized] = useState(false);
  const [pca] = useState(() => getMsalInstance());

  useEffect(() => {
    const init = async () => {
      await pca.initialize();

      // Set the first account as the active account if there is one after redirect
      const accounts = pca.getAllAccounts();
      if (accounts.length > 0) {
        pca.setActiveAccount(accounts[0]);
      }

      // Listen for login success to set the active account
      pca.addEventCallback((event: EventMessage) => {
        if (event.eventType === EventType.LOGIN_SUCCESS && event.payload) {
          const result = event.payload as AuthenticationResult;
          pca.setActiveAccount(result.account);
        }
      });

      setIsInitialized(true);
    };

    init();
  }, [pca]);

  if (!isInitialized) {
    return null;
  }

  return <MsalProvider instance={pca}>{children}</MsalProvider>;
}
