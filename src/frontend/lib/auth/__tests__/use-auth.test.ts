import { renderHook } from '@testing-library/react';
import { InteractionStatus } from '@azure/msal-browser';

// Mock MSAL React
const mockLoginRedirect = jest.fn();
const mockLogoutRedirect = jest.fn();
const mockAcquireTokenSilent = jest.fn();

jest.mock('@azure/msal-react', () => ({
  useMsal: jest.fn(),
  useIsAuthenticated: jest.fn(),
}));

import { useMsal, useIsAuthenticated } from '@azure/msal-react';

// Must import useAuth after mocks are set up
import { useAuth } from '../use-auth';

const mockedUseMsal = useMsal as jest.MockedFunction<typeof useMsal>;
const mockedUseIsAuthenticated = useIsAuthenticated as jest.MockedFunction<typeof useIsAuthenticated>;

function setupMsal({
  isAuthenticated = false,
  inProgress = InteractionStatus.None,
  accounts = [] as Array<{ name: string; username: string; localAccountId: string; idTokenClaims?: Record<string, unknown> }>,
} = {}) {
  mockedUseIsAuthenticated.mockReturnValue(isAuthenticated);
  mockedUseMsal.mockReturnValue({
    instance: {
      loginRedirect: mockLoginRedirect,
      logoutRedirect: mockLogoutRedirect,
      acquireTokenSilent: mockAcquireTokenSilent,
      acquireTokenRedirect: jest.fn(),
    } as unknown as ReturnType<typeof useMsal>['instance'],
    accounts,
    inProgress,
  });
}

describe('useAuth', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('returns isAuthenticated=false when not logged in', () => {
    setupMsal({ isAuthenticated: false });
    const { result } = renderHook(() => useAuth());

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
    expect(result.current.isLoading).toBe(false);
  });

  it('returns isLoading=true when interaction is in progress', () => {
    setupMsal({ inProgress: InteractionStatus.HandleRedirect });
    const { result } = renderHook(() => useAuth());

    expect(result.current.isLoading).toBe(true);
  });

  it('returns user info when authenticated', () => {
    setupMsal({
      isAuthenticated: true,
      accounts: [
        {
          name: 'Test User',
          username: 'test@example.com',
          localAccountId: 'user-123',
          idTokenClaims: {
            oid: 'oid-123',
            roles: ['Portal.User', 'Portal.Admin'],
          },
        },
      ],
    });
    const { result } = renderHook(() => useAuth());

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user).toEqual({
      name: 'Test User',
      email: 'test@example.com',
      oid: 'oid-123',
      roles: ['Portal.User', 'Portal.Admin'],
    });
  });

  it('login calls instance.loginRedirect', async () => {
    setupMsal({ isAuthenticated: false });
    const { result } = renderHook(() => useAuth());

    await result.current.login();
    expect(mockLoginRedirect).toHaveBeenCalled();
  });

  it('logout calls instance.logoutRedirect', async () => {
    setupMsal({ isAuthenticated: true, accounts: [{ name: 'User', username: 'u@e.com', localAccountId: 'a' }] });
    const { result } = renderHook(() => useAuth());

    await result.current.logout();
    expect(mockLogoutRedirect).toHaveBeenCalled();
  });

  it('getToken returns access token on success', async () => {
    mockAcquireTokenSilent.mockResolvedValue({ accessToken: 'mock-token' });
    setupMsal({
      isAuthenticated: true,
      accounts: [{ name: 'User', username: 'u@e.com', localAccountId: 'a' }],
    });
    const { result } = renderHook(() => useAuth());

    const token = await result.current.getToken();
    expect(token).toBe('mock-token');
  });

  it('getToken returns null when not authenticated', async () => {
    setupMsal({ isAuthenticated: false });
    const { result } = renderHook(() => useAuth());

    const token = await result.current.getToken();
    expect(token).toBeNull();
  });

  it('returns user with empty roles when none in claims', () => {
    setupMsal({
      isAuthenticated: true,
      accounts: [
        {
          name: 'No Roles User',
          username: 'noroles@example.com',
          localAccountId: 'user-456',
          idTokenClaims: { oid: 'oid-456' },
        },
      ],
    });
    const { result } = renderHook(() => useAuth());

    expect(result.current.user?.roles).toEqual([]);
  });
});
