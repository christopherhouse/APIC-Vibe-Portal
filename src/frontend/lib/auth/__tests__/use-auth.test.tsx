import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import type { RuntimeConfig } from '@/app/api/config/route';

// Mock runtime config before other imports
const mockRuntimeConfig: RuntimeConfig = {
  msal: {
    clientId: 'test-client-id',
    authority: 'https://login.microsoftonline.com/test-tenant',
    redirectUri: 'http://localhost:3000',
  },
  bffApiScope: 'api://test-bff/.default',
};

jest.mock('@/lib/config/runtime-config', () => ({
  getRuntimeConfig: jest.fn().mockResolvedValue(mockRuntimeConfig),
  clearConfigCache: jest.fn(),
}));

// Setup MSAL mocks
const mockLoginRedirect = jest.fn();
const mockLogoutRedirect = jest.fn();
const mockAcquireTokenSilent = jest.fn();
const mockGetActiveAccount = jest.fn();

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
    instance: {
      loginRedirect: mockLoginRedirect,
      logoutRedirect: mockLogoutRedirect,
      acquireTokenSilent: mockAcquireTokenSilent,
      getActiveAccount: mockGetActiveAccount,
    },
    inProgress: 'none',
  }),
  useIsAuthenticated: jest.fn(),
}));

// Must import after mocks are set up
import { useAuth } from '../use-auth';
import { useIsAuthenticated } from '@azure/msal-react';

const mockUseIsAuthenticated = useIsAuthenticated as jest.MockedFunction<typeof useIsAuthenticated>;

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

describe('useAuth', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseIsAuthenticated.mockReturnValue(false);
    mockGetActiveAccount.mockReturnValue(null);
  });

  it('returns isAuthenticated=false when not logged in', () => {
    mockUseIsAuthenticated.mockReturnValue(false);
    render(<TestComponent />);
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

    render(<TestComponent />);
    expect(screen.getByTestId('authenticated')).toHaveTextContent('true');
    expect(screen.getByTestId('user-name')).toHaveTextContent('Test User');
    expect(screen.getByTestId('user-email')).toHaveTextContent('test@example.com');
  });

  it('returns user=null when no active account', () => {
    mockUseIsAuthenticated.mockReturnValue(false);
    mockGetActiveAccount.mockReturnValue(null);

    render(<TestComponent />);
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

    render(<RolesComponent />);
    expect(screen.getByTestId('roles')).toHaveTextContent('Portal.Admin,Portal.User');
  });

  it('returns isLoading=false when inProgress is none', () => {
    render(<TestComponent />);
    expect(screen.getByTestId('loading')).toHaveTextContent('false');
  });
});

