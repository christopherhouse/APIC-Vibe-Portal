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

  it('does not store auth state in cookies', () => {
    expect(msalConfig.cache?.storeAuthStateInCookie).toBe(false);
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
