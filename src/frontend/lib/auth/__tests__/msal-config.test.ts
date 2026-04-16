import { msalConfig, loginRequest, bffApiScope } from '../msal-config';

describe('msal-config', () => {
  it('exports a valid MSAL configuration object', () => {
    expect(msalConfig).toBeDefined();
    expect(msalConfig.auth).toBeDefined();
    expect(msalConfig.auth.clientId).toBeDefined();
    expect(msalConfig.auth.authority).toBeDefined();
    expect(msalConfig.auth.redirectUri).toBeDefined();
  });

  it('uses sessionStorage for cache', () => {
    expect(msalConfig.cache?.cacheLocation).toBe('sessionStorage');
  });

  it('does not configure cookie-based cache (sessionStorage only)', () => {
    // MSAL v5 removed storeAuthStateInCookie; sessionStorage-only is the default
    expect(msalConfig.cache?.cacheLocation).toBe('sessionStorage');
  });

  it('exports loginRequest with scopes', () => {
    expect(loginRequest).toBeDefined();
    expect(loginRequest.scopes).toBeInstanceOf(Array);
    expect(loginRequest.scopes.length).toBeGreaterThan(0);
  });

  it('exports bffApiScope', () => {
    expect(typeof bffApiScope).toBe('string');
  });
});

describe('msal-config validation', () => {
  const originalEnv = process.env;

  beforeEach(() => {
    jest.resetModules();
    process.env = { ...originalEnv };
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  it('logs error when NEXT_PUBLIC_MSAL_CLIENT_ID is missing', async () => {
    delete process.env.NEXT_PUBLIC_MSAL_CLIENT_ID;
    delete process.env.NEXT_PUBLIC_MSAL_AUTHORITY;
    const errorSpy = jest.spyOn(console, 'error').mockImplementation();

    // Re-import to re-trigger validation
    await import('../msal-config');

    expect(errorSpy).toHaveBeenCalledWith(expect.stringContaining('NEXT_PUBLIC_MSAL_CLIENT_ID'));
    errorSpy.mockRestore();
  });

  it('does not log error when required env vars are set', async () => {
    process.env.NEXT_PUBLIC_MSAL_CLIENT_ID = 'test-client-id';
    process.env.NEXT_PUBLIC_MSAL_AUTHORITY = 'https://login.microsoftonline.com/test-tenant';
    const errorSpy = jest.spyOn(console, 'error').mockImplementation();

    await import('../msal-config');

    expect(errorSpy).not.toHaveBeenCalledWith(expect.stringContaining('[MSAL Config]'));
    errorSpy.mockRestore();
  });
});
