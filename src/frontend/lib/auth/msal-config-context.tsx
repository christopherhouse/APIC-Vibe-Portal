'use client';

/**
 * React context for sharing MSAL runtime configuration.
 *
 * The configuration is fetched once during app initialization and shared
 * throughout the React tree via this context.
 */

import React, { createContext, useContext } from 'react';
import type { MsalConfig } from './msal-config';

const MsalConfigContext = createContext<MsalConfig | null>(null);

export function MsalConfigProvider({
  config,
  children,
}: {
  config: MsalConfig;
  children: React.ReactNode;
}) {
  return <MsalConfigContext.Provider value={config}>{children}</MsalConfigContext.Provider>;
}

/**
 * Hook to access runtime MSAL configuration.
 * Must be used within MsalConfigProvider.
 */
export function useMsalConfig(): MsalConfig {
  const config = useContext(MsalConfigContext);
  if (!config) {
    throw new Error('useMsalConfig must be used within MsalConfigProvider');
  }
  return config;
}
