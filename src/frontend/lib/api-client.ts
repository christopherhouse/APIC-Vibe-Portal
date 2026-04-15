/**
 * Typed BFF API client for the APIC Vibe Portal.
 *
 * Provides a fetch wrapper with typed request/response handling,
 * error handling, and auth token injection placeholder.
 */

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
}

/**
 * Get the authorization header value.
 * Placeholder for Entra ID integration — returns undefined until auth is configured.
 */
function getAuthToken(): string | undefined {
  // TODO: Integrate with Entra ID authentication (task 016)
  return undefined;
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
  const { body, params, headers: customHeaders, ...fetchOptions } = options;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    ...(customHeaders as Record<string, string>),
  };

  const token = getAuthToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
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
