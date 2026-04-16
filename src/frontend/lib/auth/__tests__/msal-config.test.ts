import { fetchMsalConfig, buildMsalConfig, buildLoginRequest, type MsalConfig } from '../msal-config';

// Mock fetch globally
const mockFetch = jest.fn();
global.fetch = mockFetch;

describe('fetchMsalConfig', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('fetches MSAL config from API endpoint', async () => {
    const testConfig: MsalConfig = {
      clientId: 'test-client-id',
      authority: 'https://login.microsoftonline.com/test-tenant',
      redirectUri: 'http://localhost:3000',
      bffApiScope: 'api://test-bff/.default',
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => testConfig,
    } as Response);

    const result = await fetchMsalConfig();

    expect(mockFetch).toHaveBeenCalledWith('/api/config/msal');
    expect(result).toEqual(testConfig);
  });

  it('throws error when fetch fails', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
    } as Response);

    await expect(fetchMsalConfig()).rejects.toThrow('Failed to fetch MSAL config: 500 Internal Server Error');
  });

  it('throws error when network request fails', async () => {
    const networkError = new Error('Network error');
    mockFetch.mockRejectedValueOnce(networkError);

    await expect(fetchMsalConfig()).rejects.toThrow('Network error');
  });
});

describe('buildMsalConfig', () => {
  it('builds valid MSAL browser configuration from runtime config', () => {
    const runtimeConfig: MsalConfig = {
      clientId: 'test-client-id',
      authority: 'https://login.microsoftonline.com/test-tenant',
      redirectUri: 'http://localhost:3000',
      bffApiScope: 'api://test-bff/.default',
    };

    const msalConfig = buildMsalConfig(runtimeConfig);

    expect(msalConfig).toBeDefined();
    expect(msalConfig.auth).toBeDefined();
    expect(msalConfig.auth.clientId).toBe('test-client-id');
    expect(msalConfig.auth.authority).toBe('https://login.microsoftonline.com/test-tenant');
    expect(msalConfig.auth.redirectUri).toBe('http://localhost:3000');
    expect(msalConfig.auth.postLogoutRedirectUri).toBe('http://localhost:3000');
  });

  it('uses sessionStorage for cache', () => {
    const runtimeConfig: MsalConfig = {
      clientId: 'test-client-id',
      authority: 'https://login.microsoftonline.com/test-tenant',
      redirectUri: 'http://localhost:3000',
      bffApiScope: 'api://test-bff/.default',
    };

    const msalConfig = buildMsalConfig(runtimeConfig);

    expect(msalConfig.cache?.cacheLocation).toBe('sessionStorage');
  });

  it('configures logger options', () => {
    const runtimeConfig: MsalConfig = {
      clientId: 'test-client-id',
      authority: 'https://login.microsoftonline.com/test-tenant',
      redirectUri: 'http://localhost:3000',
      bffApiScope: 'api://test-bff/.default',
    };

    const msalConfig = buildMsalConfig(runtimeConfig);

    expect(msalConfig.system?.loggerOptions).toBeDefined();
    expect(msalConfig.system?.loggerOptions?.logLevel).toBeDefined();
    expect(msalConfig.system?.loggerOptions?.loggerCallback).toBeDefined();
  });
});

describe('buildLoginRequest', () => {
  it('builds login request with BFF API scope when provided', () => {
    const config: MsalConfig = {
      clientId: 'test-client-id',
      authority: 'https://login.microsoftonline.com/test-tenant',
      redirectUri: 'http://localhost:3000',
      bffApiScope: 'api://test-bff/.default',
    };

    const loginRequest = buildLoginRequest(config);

    expect(loginRequest).toBeDefined();
    expect(loginRequest.scopes).toBeInstanceOf(Array);
    expect(loginRequest.scopes).toEqual(['api://test-bff/.default']);
  });

  it('builds login request with default scopes when BFF API scope is empty', () => {
    const config: MsalConfig = {
      clientId: 'test-client-id',
      authority: 'https://login.microsoftonline.com/test-tenant',
      redirectUri: 'http://localhost:3000',
      bffApiScope: '',
    };

    const loginRequest = buildLoginRequest(config);

    expect(loginRequest.scopes).toEqual(['openid', 'profile', 'email']);
  });

  it('builds login request with default scopes when BFF API scope is not provided', () => {
    const config: MsalConfig = {
      clientId: 'test-client-id',
      authority: 'https://login.microsoftonline.com/test-tenant',
      redirectUri: 'http://localhost:3000',
      bffApiScope: '',
    };

    const loginRequest = buildLoginRequest(config);

    expect(loginRequest.scopes).toEqual(['openid', 'profile', 'email']);
  });
});
