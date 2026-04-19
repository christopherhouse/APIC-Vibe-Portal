'use client';

/**
 * Sidebar context provider.
 *
 * Manages the open/collapsed state of the navigation sidebar and exposes a
 * `toggle` action so any component in the tree can show or hide the sidebar.
 *
 * Wrap your application (or the root layout) with <SidebarProvider> so that
 * the Header hamburger button and the Sidebar itself share the same state.
 */

import React, { createContext, useCallback, useContext, useState } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface SidebarContextValue {
  /** True when the sidebar is fully expanded; false when collapsed to icons. */
  isOpen: boolean;
  /** Toggle the sidebar between expanded and collapsed. */
  toggle: () => void;
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const SidebarContext = createContext<SidebarContextValue | null>(null);

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function SidebarProvider({ children }: { children: React.ReactNode }) {
  const [isOpen, setIsOpen] = useState(true);

  const toggle = useCallback(() => setIsOpen((prev) => !prev), []);

  return <SidebarContext.Provider value={{ isOpen, toggle }}>{children}</SidebarContext.Provider>;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useSidebarContext(): SidebarContextValue {
  const ctx = useContext(SidebarContext);
  if (!ctx) {
    throw new Error('useSidebarContext must be used within a SidebarProvider');
  }
  return ctx;
}
