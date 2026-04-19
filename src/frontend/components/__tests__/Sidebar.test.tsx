import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock useAuth
const mockUseAuth = jest.fn();
jest.mock('@/lib/auth/use-auth', () => ({
  useAuth: () => mockUseAuth(),
}));

jest.mock('next/navigation', () => ({
  usePathname: () => '/catalog',
}));

import Sidebar from '../layout/Sidebar';

const noUser = { isAuthenticated: true, user: null };
const regularUser = { isAuthenticated: true, user: { name: 'Dev', email: 'd@x.com', id: 'u1', roles: ['Portal.User'] } };
const adminUser = { isAuthenticated: true, user: { name: 'Admin', email: 'a@x.com', id: 'u2', roles: ['Portal.Admin'] } };

describe('Sidebar', () => {
  beforeEach(() => jest.clearAllMocks());

  it('renders main navigation items', () => {
    mockUseAuth.mockReturnValue(regularUser);
    render(<Sidebar />);
    expect(screen.getByText('API Catalog')).toBeInTheDocument();
    expect(screen.getByText('Home')).toBeInTheDocument();
    expect(screen.getByText('AI Assistant')).toBeInTheDocument();
  });

  it('does NOT show admin section for non-admin users', () => {
    mockUseAuth.mockReturnValue(regularUser);
    render(<Sidebar />);
    expect(screen.queryByText('Access Policies')).not.toBeInTheDocument();
    expect(screen.queryByText('Admin')).not.toBeInTheDocument();
  });

  it('does NOT show admin section when user has no roles', () => {
    mockUseAuth.mockReturnValue(noUser);
    render(<Sidebar />);
    expect(screen.queryByText('Access Policies')).not.toBeInTheDocument();
  });

  it('shows admin section for Portal.Admin users', () => {
    mockUseAuth.mockReturnValue(adminUser);
    render(<Sidebar />);
    expect(screen.getByText('Access Policies')).toBeInTheDocument();
    expect(screen.getByText('Admin')).toBeInTheDocument();
  });

  it('Access Policies link points to correct href', () => {
    mockUseAuth.mockReturnValue(adminUser);
    render(<Sidebar />);
    const link = screen.getByRole('link', { name: /access policies/i });
    expect(link).toHaveAttribute('href', '/admin/access-policies');
  });
});
