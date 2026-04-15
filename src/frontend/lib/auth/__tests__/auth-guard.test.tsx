import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock useAuth before importing AuthGuard
const mockLogin = jest.fn();
const mockUseAuth = jest.fn();

jest.mock('../use-auth', () => ({
  useAuth: () => mockUseAuth(),
}));

import AuthGuard from '../auth-guard';

describe('AuthGuard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('shows loading spinner while auth is in progress', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: true,
      login: mockLogin,
      user: null,
    });

    render(
      <AuthGuard>
        <div data-testid="protected">Protected Content</div>
      </AuthGuard>
    );

    expect(screen.queryByTestId('protected')).not.toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('triggers login when not authenticated and not loading', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
      login: mockLogin,
      user: null,
    });

    render(
      <AuthGuard>
        <div data-testid="protected">Protected Content</div>
      </AuthGuard>
    );

    expect(mockLogin).toHaveBeenCalled();
    expect(screen.queryByTestId('protected')).not.toBeInTheDocument();
  });

  it('renders children when authenticated', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      login: mockLogin,
      user: { name: 'Test User', email: 'test@test.com', id: '1', roles: ['Portal.User'] },
    });

    render(
      <AuthGuard>
        <div data-testid="protected">Protected Content</div>
      </AuthGuard>
    );

    expect(screen.getByTestId('protected')).toBeInTheDocument();
    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });

  it('shows access denied when user lacks required roles', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      login: mockLogin,
      user: { name: 'Test User', email: 'test@test.com', id: '1', roles: ['Portal.User'] },
    });

    render(
      <AuthGuard requiredRoles={['Portal.Admin']}>
        <div data-testid="protected">Admin Content</div>
      </AuthGuard>
    );

    expect(screen.queryByTestId('protected')).not.toBeInTheDocument();
    expect(screen.getByText('Access Denied')).toBeInTheDocument();
  });

  it('renders children when user has one of the required roles', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      login: mockLogin,
      user: { name: 'Admin', email: 'admin@test.com', id: '2', roles: ['Portal.Admin', 'Portal.User'] },
    });

    render(
      <AuthGuard requiredRoles={['Portal.Admin']}>
        <div data-testid="protected">Admin Content</div>
      </AuthGuard>
    );

    expect(screen.getByTestId('protected')).toBeInTheDocument();
  });

  it('renders children when no required roles specified', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      login: mockLogin,
      user: { name: 'User', email: 'user@test.com', id: '3', roles: [] },
    });

    render(
      <AuthGuard>
        <div data-testid="protected">Any Auth Content</div>
      </AuthGuard>
    );

    expect(screen.getByTestId('protected')).toBeInTheDocument();
  });
});
