/**
 * Typed BFF API client for the APIC Vibe Portal.
 *
 * Provides a fetch wrapper with typed request/response handling,
 * error handling, and auth token injection via MSAL.
 */

import { getMsalInstance } from '@/lib/auth/auth-provider';
import { bffApiScope } from '@/lib/auth/msal-config';

const BFF_BASE_URL = process.env.NEXT_PUBLIC_BFF_URL ?? 'http://localhost:8000';

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

    const result = await msalInstance.acquireTokenSilent({
      scopes: bffApiScope ? [bffApiScope] : ['openid', 'profile', 'email'],
      account,
    });
    return result.accessToken;
  } catch {
    return undefined;
  }
}

/**
 * Build a full URL from a path and optional query parameters.
 */
function buildUrl(path: string, params?: Record<string, string>): string {
  const url = new URL(path, BFF_BASE_URL);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      url.searchParams.set(key, value);
    });
  }
  return url.toString();
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
