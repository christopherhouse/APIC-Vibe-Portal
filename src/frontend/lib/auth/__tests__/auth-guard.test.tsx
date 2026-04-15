import { render, screen } from '../../../__tests__/test-utils';

// Mock useAuth hook
const mockLogin = jest.fn();
const mockLogout = jest.fn();
const mockGetToken = jest.fn();

jest.mock('../use-auth', () => ({
  useAuth: jest.fn(),
}));

import { useAuth } from '../use-auth';
import AuthGuard from '../auth-guard';

const mockedUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;

function setupAuth({
  isAuthenticated = false,
  isLoading = false,
  user = null as { name: string; email: string; oid: string; roles: string[] } | null,
} = {}) {
  mockedUseAuth.mockReturnValue({
    isAuthenticated,
    isLoading,
    user,
    login: mockLogin,
    logout: mockLogout,
    getToken: mockGetToken,
  });
}

describe('AuthGuard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('shows loading state while auth is initializing', () => {
    setupAuth({ isLoading: true });
    render(
      <AuthGuard>
        <div>Protected Content</div>
      </AuthGuard>
    );

    expect(screen.getByText('Checking authentication…')).toBeInTheDocument();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('triggers login when not authenticated', () => {
    setupAuth({ isAuthenticated: false, isLoading: false });
    render(
      <AuthGuard>
        <div>Protected Content</div>
      </AuthGuard>
    );

    expect(mockLogin).toHaveBeenCalled();
    expect(screen.getByText('Redirecting to login…')).toBeInTheDocument();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('renders children when authenticated', () => {
    setupAuth({
      isAuthenticated: true,
      user: { name: 'Test', email: 'test@e.com', oid: 'x', roles: ['Portal.User'] },
    });
    render(
      <AuthGuard>
        <div>Protected Content</div>
      </AuthGuard>
    );

    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });

  it('shows access denied when user lacks required roles', () => {
    setupAuth({
      isAuthenticated: true,
      user: { name: 'Test', email: 'test@e.com', oid: 'x', roles: ['Portal.User'] },
    });
    render(
      <AuthGuard requiredRoles={['Portal.Admin']}>
        <div>Admin Content</div>
      </AuthGuard>
    );

    expect(screen.getByText('Access Denied')).toBeInTheDocument();
    expect(screen.queryByText('Admin Content')).not.toBeInTheDocument();
  });

  it('renders children when user has required role', () => {
    setupAuth({
      isAuthenticated: true,
      user: { name: 'Admin', email: 'admin@e.com', oid: 'x', roles: ['Portal.Admin'] },
    });
    render(
      <AuthGuard requiredRoles={['Portal.Admin']}>
        <div>Admin Content</div>
      </AuthGuard>
    );

    expect(screen.getByText('Admin Content')).toBeInTheDocument();
  });

  it('renders custom access denied fallback', () => {
    setupAuth({
      isAuthenticated: true,
      user: { name: 'Test', email: 'test@e.com', oid: 'x', roles: [] },
    });
    render(
      <AuthGuard
        requiredRoles={['Portal.Admin']}
        accessDeniedFallback={<div>Custom Denied</div>}
      >
        <div>Content</div>
      </AuthGuard>
    );

    expect(screen.getByText('Custom Denied')).toBeInTheDocument();
  });
});
