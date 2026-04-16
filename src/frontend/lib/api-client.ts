/**
 * Typed BFF API client for the APIC Vibe Portal.
 *
 * Provides a fetch wrapper with typed request/response handling,
 * error handling, and auth token injection via MSAL.
 */

import { getMsalInstance } from '@/lib/auth/auth-provider';
import { getRuntimeConfig } from '@/lib/config/runtime-config';

/** Custom error type for API errors. */
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public statusText: string,
    public body?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/** Request options extending standard fetch RequestInit. */
export interface ApiRequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown;
  params?: Record<string, string>;
  /** Skip auth token injection (e.g. for public endpoints). */
  skipAuth?: boolean;
}

/**
 * Acquire an access token from MSAL for the BFF API.
 * Returns `undefined` when no active account exists or token acquisition fails.
 */
async function getAuthToken(): Promise<string | undefined> {
  try {
    const msalInstance = getMsalInstance();
    const account = msalInstance.getActiveAccount();
    if (!account) return undefined;

    const config = await getRuntimeConfig();
    const scopes = config.bffApiScope ? [config.bffApiScope] : ['openid', 'profile', 'email'];

    const result = await msalInstance.acquireTokenSilent({
      scopes,
      account,
    });
    return result.accessToken;
  } catch {
    return undefined;
  }
}

/**
 * Build a relative URL from a path and optional query parameters.
 *
 * All BFF requests now go through the catch-all proxy route (`app/api/[...path]/route.ts`)
 * on the same origin, so we only need a relative path — no absolute base URL.
 */
function buildUrl(path: string, params?: Record<string, string>): string {
  const searchParams = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      searchParams.set(key, value);
    });
  }
  const query = searchParams.toString();
  return query ? `${path}?${query}` : path;
}

/**
 * Core fetch wrapper with typed responses and error handling.
 */
async function request<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const { body, params, headers: customHeaders, skipAuth, ...fetchOptions } = options;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    ...(customHeaders as Record<string, string>),
  };

  if (!skipAuth) {
    const token = await getAuthToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }

  const url = buildUrl(path, params);

  const response = await fetch(url, {
    ...fetchOptions,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    let errorBody: unknown;
    try {
      errorBody = await response.json();
    } catch {
      // Response body is not JSON
    }
    throw new ApiError(
      `API request failed: ${response.status} ${response.statusText}`,
      response.status,
      response.statusText,
      errorBody
    );
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

/** API client with typed HTTP methods. */
export const apiClient = {
  get<T>(path: string, options?: ApiRequestOptions): Promise<T> {
    return request<T>(path, { ...options, method: 'GET' });
  },

  post<T>(path: string, body?: unknown, options?: ApiRequestOptions): Promise<T> {
    return request<T>(path, { ...options, method: 'POST', body });
  },

  put<T>(path: string, body?: unknown, options?: ApiRequestOptions): Promise<T> {
    return request<T>(path, { ...options, method: 'PUT', body });
  },

  patch<T>(path: string, body?: unknown, options?: ApiRequestOptions): Promise<T> {
    return request<T>(path, { ...options, method: 'PATCH', body });
  },

  delete<T>(path: string, options?: ApiRequestOptions): Promise<T> {
    return request<T>(path, { ...options, method: 'DELETE' });
  },
};
