'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import type { ApiDefinition, ApiVersion, ApiDeployment } from '@apic-vibe-portal/shared';
import {
  fetchApiDetail,
  fetchApiVersions,
  fetchApiDeployments,
  fetchApiDefinition,
} from '@/lib/catalog-detail-api';

export interface ApiDetailState {
  api: ApiDefinition | null;
  versions: ApiVersion[];
  deployments: ApiDeployment[];
  specContent: string | null;
  selectedVersionId: string | null;
  isLoading: boolean;
  isSpecLoading: boolean;
  error: string | null;
  specError: string | null;
}

const INITIAL_STATE: ApiDetailState = {
  api: null,
  versions: [],
  deployments: [],
  specContent: null,
  selectedVersionId: null,
  isLoading: true,
  isSpecLoading: false,
  error: null,
  specError: null,
};

export interface UseApiDetailOptions {
  /** When false the hook returns initial state without calling the API. */
  enabled?: boolean;
}

/**
 * React hook for fetching API detail data.
 * Loads API detail, versions, and deployments in parallel on mount.
 * Provides version selection and spec loading.
 *
 * When `enabled` is `false` (e.g. user is not authenticated) the hook skips
 * API calls and returns the initial empty state.
 */
export function useApiDetail(apiId: string, { enabled = true }: UseApiDetailOptions = {}) {
  const [state, setState] = useState<ApiDetailState>({
    ...INITIAL_STATE,
    isLoading: enabled,
  });
  const mountedRef = useRef(true);
  const latestSpecRequestRef = useRef<string | null>(null);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  // Load detail, versions, and deployments in parallel
  const loadAll = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      const [api, versions, deployments] = await Promise.all([
        fetchApiDetail(apiId),
        fetchApiVersions(apiId),
        fetchApiDeployments(apiId),
      ]);

      if (!mountedRef.current) return;

      const defaultVersion = versions.length > 0 ? versions[0].id : null;

      setState((prev) => ({
        ...prev,
        api,
        versions,
        deployments,
        selectedVersionId: defaultVersion,
        isLoading: false,
        error: null,
      }));

      // Auto-load spec for first version
      if (defaultVersion) {
        void loadSpec(apiId, defaultVersion);
      }
    } catch (err) {
      if (!mountedRef.current) return;
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: err instanceof Error ? err.message : 'Failed to load API details',
      }));
    }
  }, [apiId]);

  // Load spec for a specific version
  const loadSpec = useCallback(async (id: string, versionId: string) => {
    latestSpecRequestRef.current = versionId;
    setState((prev) => ({ ...prev, isSpecLoading: true, specError: null }));
    try {
      const specContent = await fetchApiDefinition(id, versionId);
      if (!mountedRef.current) return;
      // Ignore stale responses from earlier version requests
      if (latestSpecRequestRef.current !== versionId) return;
      setState((prev) => ({
        ...prev,
        specContent,
        isSpecLoading: false,
        specError: null,
      }));
    } catch (err) {
      if (!mountedRef.current) return;
      if (latestSpecRequestRef.current !== versionId) return;
      setState((prev) => ({
        ...prev,
        specContent: null,
        isSpecLoading: false,
        specError: err instanceof Error ? err.message : 'Failed to load specification',
      }));
    }
  }, []);

  // Select a different version and load its spec
  const selectVersion = useCallback(
    (versionId: string) => {
      setState((prev) => ({ ...prev, selectedVersionId: versionId }));
      void loadSpec(apiId, versionId);
    },
    [apiId, loadSpec]
  );

  useEffect(() => {
    if (!enabled) {
      setState({ ...INITIAL_STATE, isLoading: false });
      return;
    }
    void loadAll();
  }, [loadAll, enabled]);

  return {
    ...state,
    selectVersion,
    refetch: loadAll,
  };
}
