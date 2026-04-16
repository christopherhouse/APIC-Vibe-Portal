'use client';

/**
 * MSAL authentication provider that wraps the application.
 *
 * Fetches runtime configuration from the server, then initialises a
 * `PublicClientApplication` singleton and provides it to the React tree
 * via `MsalProvider`.
 */

import React, { useEffect, useState } from 'react';
import {
  PublicClientApplication,
  EventType,
  type EventMessage,
  type AuthenticationResult,
} from '@azure/msal-browser';
import { MsalProvider } from '@azure/msal-react';
import { getRuntimeConfig } from '@/lib/config/runtime-config';
import { buildMsalConfig } from './msal-config';

let msalInstance: PublicClientApplication | null = null;

/**
 * Get (or create) the singleton MSAL PublicClientApplication instance.
 *
 * IMPORTANT: This must only be called after runtime config is fetched.
 */
export function getMsalInstance(): PublicClientApplication {
  if (!msalInstance) {
    throw new Error('MSAL instance accessed before initialization. Call initMsalInstance() first.');
  }
  return msalInstance;
}

/**
 * Initialize the MSAL instance with runtime config.
 * This is called by AuthProvider during startup.
 */
async function initMsalInstance(): Promise<PublicClientApplication> {
  if (msalInstance) {
    return msalInstance;
  }

  const config = await getRuntimeConfig();
  const msalConfig = buildMsalConfig(config);
  msalInstance = new PublicClientApplication(msalConfig);
  return msalInstance;
}

/**
 * AuthProvider fetches runtime config, initialises MSAL, and wraps the
 * React tree in `MsalProvider`.
 *
 * It waits for both config fetch and `msalInstance.initialize()` to
 * complete before rendering children.
 */
export default function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isInitialized, setIsInitialized] = useState(false);
  const [pca, setPca] = useState<PublicClientApplication | null>(null);

  useEffect(() => {
    const init = async () => {
      // Fetch runtime config and create MSAL instance
      const instance = await initMsalInstance();

      // Initialize MSAL
      await instance.initialize();

      // Set the first account as the active account if there is one after redirect
      const accounts = instance.getAllAccounts();
      if (accounts.length > 0) {
        instance.setActiveAccount(accounts[0]);
      }

      // Listen for login success to set the active account
      instance.addEventCallback((event: EventMessage) => {
        if (event.eventType === EventType.LOGIN_SUCCESS && event.payload) {
          const result = event.payload as AuthenticationResult;
          instance.setActiveAccount(result.account);
        }
      });

      setPca(instance);
      setIsInitialized(true);
    };

    init().catch((error) => {
      console.error('[AuthProvider] Failed to initialize MSAL:', error);
    });
  }, []);

  if (!isInitialized || !pca) {
    return null;
  }

  return <MsalProvider instance={pca}>{children}</MsalProvider>;
}
