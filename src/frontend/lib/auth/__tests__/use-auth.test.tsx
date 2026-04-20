import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';

// Setup MSAL mocks
const mockLoginRedirect = jest.fn();
const mockLogoutRedirect = jest.fn();
const mockAcquireTokenSilent = jest.fn();
const mockGetActiveAccount = jest.fn();

// Stable reference so useEffect deps don't trigger infinite re-renders
const mockInstance = {
  loginRedirect: mockLoginRedirect,
  logoutRedirect: mockLogoutRedirect,
  acquireTokenSilent: mockAcquireTokenSilent,
  getActiveAccount: mockGetActiveAccount,
};

jest.mock('@azure/msal-browser', () => ({
  InteractionRequiredAuthError: class InteractionRequiredAuthError extends Error {
    constructor(message?: string) {
      super(message);
      this.name = 'InteractionRequiredAuthError';
    }
  },
  LogLevel: { Error: 0, Warning: 1, Info: 2, Verbose: 3, Trace: 4 },
}));

jest.mock('@azure/msal-react', () => ({
  useMsal: () => ({
    instance: mockInstance,
    inProgress: 'none',
  }),
  useIsAuthenticated: jest.fn(),
}));

// Must import after mocks are set up
import { useAuth } from '../use-auth';
import { useIsAuthenticated } from '@azure/msal-react';
import { MsalConfigProvider } from '../msal-config-context';
import type { MsalConfig } from '../msal-config';

const mockUseIsAuthenticated = useIsAuthenticated as jest.MockedFunction<typeof useIsAuthenticated>;

// Test MSAL configuration
const testMsalConfig: MsalConfig = {
  clientId: 'test-client-id',
  authority: 'https://login.microsoftonline.com/test-tenant',
  redirectUri: 'http://localhost:3000',
  bffApiScope: 'api://test-bff/.default',
};

// Helper component to test the hook
function TestComponent() {
  const { isAuthenticated, user, isLoading } = useAuth();
  return (
    <div>
      <span data-testid="authenticated">{String(isAuthenticated)}</span>
      <span data-testid="loading">{String(isLoading)}</span>
      <span data-testid="user-name">{user?.name ?? 'none'}</span>
      <span data-testid="user-email">{user?.email ?? 'none'}</span>
    </div>
  );
}

// Wrapper that provides MSAL config context
function TestWrapper({ children }: { children: React.ReactNode }) {
  return <MsalConfigProvider config={testMsalConfig}>{children}</MsalConfigProvider>;
}

describe('useAuth', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseIsAuthenticated.mockReturnValue(false);
    mockGetActiveAccount.mockReturnValue(null);
  });

  it('returns isAuthenticated=false when not logged in', () => {
    mockUseIsAuthenticated.mockReturnValue(false);
    render(<TestComponent />, { wrapper: TestWrapper });
    expect(screen.getByTestId('authenticated')).toHaveTextContent('false');
  });

  it('returns isAuthenticated=true when logged in', () => {
    mockUseIsAuthenticated.mockReturnValue(true);
    mockGetActiveAccount.mockReturnValue({
      name: 'Test User',
      username: 'test@example.com',
      localAccountId: 'abc-123',
      idTokenClaims: { roles: ['Portal.User'] },
    });

    render(<TestComponent />, { wrapper: TestWrapper });
    expect(screen.getByTestId('authenticated')).toHaveTextContent('true');
    expect(screen.getByTestId('user-name')).toHaveTextContent('Test User');
    expect(screen.getByTestId('user-email')).toHaveTextContent('test@example.com');
  });

  it('returns user=null when no active account', () => {
    mockUseIsAuthenticated.mockReturnValue(false);
    mockGetActiveAccount.mockReturnValue(null);

    render(<TestComponent />, { wrapper: TestWrapper });
    expect(screen.getByTestId('user-name')).toHaveTextContent('none');
  });

  it('extracts roles from idTokenClaims', () => {
    mockUseIsAuthenticated.mockReturnValue(true);
    mockGetActiveAccount.mockReturnValue({
      name: 'Admin',
      username: 'admin@example.com',
      localAccountId: 'admin-1',
      idTokenClaims: { roles: ['Portal.Admin', 'Portal.User'] },
    });

    // We need a component that exposes roles
    function RolesComponent() {
      const { user } = useAuth();
      return <span data-testid="roles">{user?.roles.join(',') ?? 'none'}</span>;
    }

    render(<RolesComponent />, { wrapper: TestWrapper });
    expect(screen.getByTestId('roles')).toHaveTextContent('Portal.Admin,Portal.User');
  });

  it('returns isLoading=false when inProgress is none', () => {
    render(<TestComponent />, { wrapper: TestWrapper });
    expect(screen.getByTestId('loading')).toHaveTextContent('false');
  });

  describe('when MSAL is not configured (empty clientId)', () => {
    const emptyConfig: MsalConfig = {
      clientId: '',
      authority: 'https://login.microsoftonline.com/common',
      redirectUri: '',
      bffApiScope: '',
    };

    function NoAuthWrapper({ children }: { children: React.ReactNode }) {
      return <MsalConfigProvider config={emptyConfig}>{children}</MsalConfigProvider>;
    }

    it('returns isAuthenticated=true even when MSAL reports unauthenticated', () => {
      mockUseIsAuthenticated.mockReturnValue(false);
      render(<TestComponent />, { wrapper: NoAuthWrapper });
      expect(screen.getByTestId('authenticated')).toHaveTextContent('true');
    });

    it('returns user=null when MSAL is not configured', () => {
      mockUseIsAuthenticated.mockReturnValue(false);
      mockGetActiveAccount.mockReturnValue(null);
      render(<TestComponent />, { wrapper: NoAuthWrapper });
      expect(screen.getByTestId('user-name')).toHaveTextContent('none');
    });
  });

  describe('access token roles fallback', () => {
    /**
     * Build a mock JWT whose payload contains the given claims.
     * The header and signature are stubs — only the payload matters.
     */
    function buildMockJwt(payload: Record<string, unknown>): string {
      const header = btoa(JSON.stringify({ alg: 'RS256', typ: 'JWT' }));
      const body = btoa(JSON.stringify(payload));
      return `${header}.${body}.fake-signature`;
    }

    it('falls back to access token roles when idTokenClaims has no roles', async () => {
      mockUseIsAuthenticated.mockReturnValue(true);
      mockGetActiveAccount.mockReturnValue({
        name: 'Admin',
        username: 'admin@example.com',
        localAccountId: 'admin-1',
        idTokenClaims: {}, // No roles in ID token
      });

      const accessToken = buildMockJwt({ roles: ['Portal.Admin'], scp: 'access_as_user' });
      mockAcquireTokenSilent.mockResolvedValue({ accessToken });

      function RolesComponent() {
        const { user } = useAuth();
        return <span data-testid="roles">{user?.roles.join(',') || 'none'}</span>;
      }

      await act(async () => {
        render(<RolesComponent />, { wrapper: TestWrapper });
      });

      await waitFor(() => {
        expect(screen.getByTestId('roles')).toHaveTextContent('Portal.Admin');
      });
    });

    it('prefers idTokenClaims roles over access token roles', async () => {
      mockUseIsAuthenticated.mockReturnValue(true);
      mockGetActiveAccount.mockReturnValue({
        name: 'Admin',
        username: 'admin@example.com',
        localAccountId: 'admin-1',
        idTokenClaims: { roles: ['Portal.User'] }, // Has roles in ID token
      });

      // Access token has different roles — should NOT be used
      const accessToken = buildMockJwt({ roles: ['Portal.Admin'] });
      mockAcquireTokenSilent.mockResolvedValue({ accessToken });

      function RolesComponent() {
        const { user } = useAuth();
        return <span data-testid="roles">{user?.roles.join(',') ?? 'none'}</span>;
      }

      await act(async () => {
        render(<RolesComponent />, { wrapper: TestWrapper });
      });

      // Should use ID token roles, not access token roles
      expect(screen.getByTestId('roles')).toHaveTextContent('Portal.User');
      // acquireTokenSilent should NOT have been called (ID token has roles)
      expect(mockAcquireTokenSilent).not.toHaveBeenCalled();
    });

    it('gracefully handles acquireTokenSilent failure', async () => {
      mockUseIsAuthenticated.mockReturnValue(true);
      mockGetActiveAccount.mockReturnValue({
        name: 'User',
        username: 'user@example.com',
        localAccountId: 'user-1',
        idTokenClaims: {}, // No roles
      });

      mockAcquireTokenSilent.mockRejectedValue(new Error('token expired'));

      function RolesComponent() {
        const { user } = useAuth();
        return <span data-testid="roles">{user?.roles.join(',') || 'none'}</span>;
      }

      await act(async () => {
        render(<RolesComponent />, { wrapper: TestWrapper });
      });

      // Should still render without crashing, roles remain empty
      expect(screen.getByTestId('roles')).toHaveTextContent('none');
    });
  });
});
