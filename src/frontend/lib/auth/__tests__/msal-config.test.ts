import { msalConfig, loginRequest, tokenRequest, bffApiScope } from '../msal-config';

describe('msal-config', () => {
  it('has a clientId from environment or empty default', () => {
    expect(typeof msalConfig.auth.clientId).toBe('string');
  });

  it('has authority configured', () => {
    expect(msalConfig.auth.authority).toContain('login.microsoftonline.com');
  });

  it('uses sessionStorage for cache', () => {
    expect(msalConfig.cache?.cacheLocation).toBe('sessionStorage');
  });

  it('loginRequest includes bffApiScope', () => {
    expect(loginRequest.scopes).toContain(bffApiScope);
  });

  it('tokenRequest includes bffApiScope', () => {
    expect(tokenRequest.scopes).toContain(bffApiScope);
  });

  it('bffApiScope has a default value', () => {
    expect(typeof bffApiScope).toBe('string');
    expect(bffApiScope.length).toBeGreaterThan(0);
  });
});
