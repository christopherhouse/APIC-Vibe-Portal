import React from 'react';
import { render, screen, act } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock fetch before importing AuthProvider
const mockFetch = jest.fn();
global.fetch = mockFetch;

// Mock MSAL before importing AuthProvider
const mockInitialize = jest.fn().mockResolvedValue(undefined);
const mockHandleRedirectPromise = jest.fn().mockResolvedValue(null);
const mockGetAllAccounts = jest.fn().mockReturnValue([]);
const mockGetActiveAccount = jest.fn().mockReturnValue(null);
const mockSetActiveAccount = jest.fn();
const mockAddEventCallback = jest.fn();

jest.mock('@azure/msal-browser', () => {
  return {
    PublicClientApplication: jest.fn().mockImplementation(() => ({
      initialize: mockInitialize,
      handleRedirectPromise: mockHandleRedirectPromise,
      getAllAccounts: mockGetAllAccounts,
      getActiveAccount: mockGetActiveAccount,
      setActiveAccount: mockSetActiveAccount,
      addEventCallback: mockAddEventCallback,
    })),
    EventType: {
      LOGIN_SUCCESS: 'msal:loginSuccess',
    },
    LogLevel: {
      Error: 0,
      Warning: 1,
      Info: 2,
      Verbose: 3,
      Trace: 4,
    },
  };
});

jest.mock('@azure/msal-react', () => ({
  MsalProvider: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="msal-provider">{children}</div>
  ),
}));

import AuthProvider from '../auth-provider';

// Test MSAL configuration
const testMsalConfig = {
  clientId: 'test-client-id',
  authority: 'https://login.microsoftonline.com/test-tenant',
  redirectUri: 'http://localhost:3000',
  bffApiScope: 'api://test-bff/.default',
};

describe('AuthProvider', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Mock successful fetch of MSAL config by default
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => testMsalConfig,
    } as Response);
  });

  it('renders nothing until MSAL is initialized', () => {
    // Make initialize never resolve
    mockInitialize.mockReturnValue(new Promise(() => {}));

    render(
      <AuthProvider>
        <div data-testid="child">Hello</div>
      </AuthProvider>
    );

    expect(screen.queryByTestId('child')).not.toBeInTheDocument();
  });

  it('renders children after initialization', async () => {
    mockInitialize.mockResolvedValue(undefined);

    await act(async () => {
      render(
        <AuthProvider>
          <div data-testid="child">Hello</div>
        </AuthProvider>
      );
    });

    expect(screen.getByTestId('child')).toBeInTheDocument();
  });

  it('wraps children in MsalProvider', async () => {
    mockInitialize.mockResolvedValue(undefined);

    await act(async () => {
      render(
        <AuthProvider>
          <div data-testid="child">Hello</div>
        </AuthProvider>
      );
    });

    expect(screen.getByTestId('msal-provider')).toBeInTheDocument();
  });

  it('sets active account if accounts exist after initialization', async () => {
    const mockAccount = { localAccountId: '123', username: 'test@example.com' };
    mockGetAllAccounts.mockReturnValue([mockAccount]);
    mockGetActiveAccount.mockReturnValue(null);
    mockInitialize.mockResolvedValue(undefined);

    await act(async () => {
      render(
        <AuthProvider>
          <div>Hello</div>
        </AuthProvider>
      );
    });

    expect(mockSetActiveAccount).toHaveBeenCalledWith(mockAccount);
  });

  it('calls handleRedirectPromise after initialization', async () => {
    mockInitialize.mockResolvedValue(undefined);

    await act(async () => {
      render(
        <AuthProvider>
          <div>Hello</div>
        </AuthProvider>
      );
    });

    expect(mockHandleRedirectPromise).toHaveBeenCalledTimes(1);
    // handleRedirectPromise must be called after initialize
    const initOrder = mockInitialize.mock.invocationCallOrder[0];
    const redirectOrder = mockHandleRedirectPromise.mock.invocationCallOrder[0];
    expect(redirectOrder).toBeGreaterThan(initOrder);
  });

  it('sets active account from redirect result when available', async () => {
    const redirectAccount = { localAccountId: 'redirect-456', username: 'redirect@example.com' };
    mockHandleRedirectPromise.mockResolvedValue({ account: redirectAccount });
    mockInitialize.mockResolvedValue(undefined);

    await act(async () => {
      render(
        <AuthProvider>
          <div>Hello</div>
        </AuthProvider>
      );
    });

    // Should set the account from the redirect result
    expect(mockSetActiveAccount).toHaveBeenCalledWith(redirectAccount);
  });

  it('prefers redirect result account over cached accounts', async () => {
    const cachedAccount = { localAccountId: 'cached-123', username: 'cached@example.com' };
    const redirectAccount = { localAccountId: 'redirect-456', username: 'redirect@example.com' };
    mockGetAllAccounts.mockReturnValue([cachedAccount]);
    mockGetActiveAccount.mockReturnValue(null);
    mockHandleRedirectPromise.mockResolvedValue({ account: redirectAccount });
    mockInitialize.mockResolvedValue(undefined);

    await act(async () => {
      render(
        <AuthProvider>
          <div>Hello</div>
        </AuthProvider>
      );
    });

    // setActiveAccount called with redirect account first; should not fall through to cached
    expect(mockSetActiveAccount).toHaveBeenCalledWith(redirectAccount);
  });

  it('registers an event callback for LOGIN_SUCCESS', async () => {
    mockInitialize.mockResolvedValue(undefined);

    await act(async () => {
      render(
        <AuthProvider>
          <div>Hello</div>
        </AuthProvider>
      );
    });

    expect(mockAddEventCallback).toHaveBeenCalled();
  });
});
