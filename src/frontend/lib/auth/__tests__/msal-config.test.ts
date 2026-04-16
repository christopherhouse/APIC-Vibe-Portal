import { buildMsalConfig, buildLoginRequest } from '../msal-config';
import type { RuntimeConfig } from '@/app/api/config/route';

describe('msal-config', () => {
  const mockConfig: RuntimeConfig = {
    msal: {
      clientId: 'test-client-id',
      authority: 'https://login.microsoftonline.com/test-tenant',
      redirectUri: 'http://localhost:3000',
    },
    bffApiScope: 'api://test-bff/.default',
  };

  describe('buildMsalConfig', () => {
    it('builds a valid MSAL configuration object from runtime config', () => {
      const msalConfig = buildMsalConfig(mockConfig);
      expect(msalConfig).toBeDefined();
      expect(msalConfig.auth).toBeDefined();
      expect(msalConfig.auth.clientId).toBe('test-client-id');
      expect(msalConfig.auth.authority).toBe('https://login.microsoftonline.com/test-tenant');
      expect(msalConfig.auth.redirectUri).toBe('http://localhost:3000');
      expect(msalConfig.auth.postLogoutRedirectUri).toBe('http://localhost:3000');
    });

    it('uses sessionStorage for cache', () => {
      const msalConfig = buildMsalConfig(mockConfig);
      expect(msalConfig.cache?.cacheLocation).toBe('sessionStorage');
    });

    it('configures logger', () => {
      const msalConfig = buildMsalConfig(mockConfig);
      expect(msalConfig.system?.loggerOptions).toBeDefined();
      expect(msalConfig.system?.loggerOptions?.loggerCallback).toBeInstanceOf(Function);
    });
  });

  describe('buildLoginRequest', () => {
    it('builds login request with BFF API scope when provided', () => {
      const loginRequest = buildLoginRequest(mockConfig);
      expect(loginRequest).toBeDefined();
      expect(loginRequest.scopes).toEqual(['api://test-bff/.default']);
    });

    it('falls back to default scopes when BFF API scope is empty', () => {
      const configWithoutScope: RuntimeConfig = {
        ...mockConfig,
        bffApiScope: '',
      };
      const loginRequest = buildLoginRequest(configWithoutScope);
      expect(loginRequest.scopes).toEqual(['openid', 'profile', 'email']);
    });
  });
});

