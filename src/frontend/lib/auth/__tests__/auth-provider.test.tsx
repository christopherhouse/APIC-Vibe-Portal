import React from 'react';
import { render, screen, act } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock MSAL before importing AuthProvider
const mockInitialize = jest.fn().mockResolvedValue(undefined);
const mockGetAllAccounts = jest.fn().mockReturnValue([]);
const mockSetActiveAccount = jest.fn();
const mockAddEventCallback = jest.fn();

jest.mock('@azure/msal-browser', () => {
  return {
    PublicClientApplication: jest.fn().mockImplementation(() => ({
      initialize: mockInitialize,
      getAllAccounts: mockGetAllAccounts,
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
  MsalProvider: ({ children }: { children: React.ReactNode }) => <div data-testid="msal-provider">{children}</div>,
}));

import AuthProvider from '../auth-provider';

describe('AuthProvider', () => {
  beforeEach(() => {
    jest.clearAllMocks();
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
