import React from 'react';
import { render, screen, waitFor } from '../../../__tests__/test-utils';
import '@testing-library/jest-dom';

const mockUseAuth = jest.fn();
jest.mock('@/lib/auth/use-auth', () => ({
  useAuth: () => mockUseAuth(),
}));

import AdminLayout from '../layout';

describe('AdminLayout', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders children when user has Portal.Admin role', async () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      login: jest.fn(),
      user: { id: 'u1', name: 'A', email: 'a@x.com', roles: ['Portal.Admin'] },
    });
    render(
      <AdminLayout>
        <div data-testid="admin-child">child</div>
      </AdminLayout>
    );
    await waitFor(() => {
      expect(screen.getByTestId('admin-child')).toBeInTheDocument();
    });
  });

  it('shows Access Denied for users without Portal.Admin', async () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      login: jest.fn(),
      user: { id: 'u1', name: 'A', email: 'a@x.com', roles: ['Portal.User'] },
    });
    render(
      <AdminLayout>
        <div data-testid="admin-child">child</div>
      </AdminLayout>
    );
    await waitFor(() => {
      expect(screen.getByText(/Access Denied/i)).toBeInTheDocument();
    });
    expect(screen.queryByTestId('admin-child')).not.toBeInTheDocument();
  });

  it('triggers login when unauthenticated', async () => {
    const login = jest.fn();
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
      login,
      user: null,
    });
    render(
      <AdminLayout>
        <div>child</div>
      </AdminLayout>
    );
    await waitFor(() => expect(login).toHaveBeenCalled());
  });
});
