'use client';

/**
 * MSAL authentication provider that wraps the application.
 *
 * Fetches MSAL configuration from the runtime API, then initializes
 * a `PublicClientApplication` singleton and provides it to the React tree via `MsalProvider`.
 */

import React, { useEffect, useState } from 'react';
import {
  PublicClientApplication,
  EventType,
  type EventMessage,
  type AuthenticationResult,
} from '@azure/msal-browser';
import { MsalProvider } from '@azure/msal-react';
import { fetchMsalConfig, buildMsalConfig, type MsalConfig } from './msal-config';
import { MsalConfigProvider } from './msal-config-context';

let msalInstance: PublicClientApplication | null = null;

/**
 * Get the MSAL instance. Throws if called before AuthProvider initialization.
 */
export function getMsalInstance(): PublicClientApplication {
  if (!msalInstance) {
    throw new Error('MSAL instance not initialized. Ensure AuthProvider is mounted.');
  }
  return msalInstance;
}

/**
 * AuthProvider fetches runtime MSAL config, initialises MSAL, and wraps
 * the React tree in `MsalProvider` and `MsalConfigProvider`.
 *
 * It waits for config fetch and `msalInstance.initialize()` to complete
 * before rendering children.
 */
export default function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isInitialized, setIsInitialized] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [config, setConfig] = useState<MsalConfig | null>(null);

  useEffect(() => {
    const init = async () => {
      try {
        // Fetch runtime MSAL configuration from API
        const runtimeConfig = await fetchMsalConfig();
        setConfig(runtimeConfig);

        // Create MSAL instance with runtime config (singleton pattern)
        if (!msalInstance) {
          const msalConfig = buildMsalConfig(runtimeConfig);
          msalInstance = new PublicClientApplication(msalConfig);
        }

        // Initialize MSAL
        await msalInstance.initialize();

        // Set the first account as the active account if there is one after redirect
        const accounts = msalInstance.getAllAccounts();
        if (accounts.length > 0) {
          msalInstance.setActiveAccount(accounts[0]);
        }

        // Listen for login success to set the active account
        msalInstance.addEventCallback((event: EventMessage) => {
          if (event.eventType === EventType.LOGIN_SUCCESS && event.payload) {
            const result = event.payload as AuthenticationResult;
            msalInstance?.setActiveAccount(result.account);
          }
        });

        setIsInitialized(true);
      } catch (err) {
        console.error('[AuthProvider] Failed to initialize MSAL:', err);
        setError(err instanceof Error ? err : new Error('Unknown error'));
      }
    };

    init();
  }, []);

  // Show error state if initialization failed
  if (error) {
    return (
      <div style={{ padding: '20px', color: 'red' }}>
        <h1>Authentication Error</h1>
        <p>Failed to initialize authentication. Please check the console for details.</p>
        <pre>{error.message}</pre>
      </div>
    );
  }

  // Show loading state while initializing
  if (!isInitialized || !config) {
    return null;
  }

  return (
    <MsalConfigProvider config={config}>
      <MsalProvider instance={msalInstance!}>{children}</MsalProvider>
    </MsalConfigProvider>
  );
}
