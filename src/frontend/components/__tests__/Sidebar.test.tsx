import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock useAuth
const mockUseAuth = jest.fn();
jest.mock('@/lib/auth/use-auth', () => ({
  useAuth: () => mockUseAuth(),
}));

jest.mock('next/navigation', () => ({
  usePathname: () => '/',
}));

jest.mock('next/link', () => {
  const MockLink = ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  );
  MockLink.displayName = 'MockLink';
  return MockLink;
});

// Mock sidebar context so we can control isOpen
const mockUseSidebarContext = jest.fn();
jest.mock('@/lib/sidebar-context', () => ({
  useSidebarContext: () => mockUseSidebarContext(),
}));

import Sidebar from '../layout/Sidebar';

const noUser = { isAuthenticated: true, user: null };
const regularUser = {
  isAuthenticated: true,
  user: { name: 'Dev', email: 'd@x.com', id: 'u1', roles: ['Portal.User'] },
};
const adminUser = {
  isAuthenticated: true,
  user: { name: 'Admin', email: 'a@x.com', id: 'u2', roles: ['Portal.Admin'] },
};

describe('Sidebar', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Default: sidebar open, regular user
    mockUseSidebarContext.mockReturnValue({ isOpen: true, toggle: jest.fn() });
    mockUseAuth.mockReturnValue(regularUser);
  });

  it('renders main navigation items', () => {
    render(<Sidebar />);
    expect(screen.getByText('API Catalog')).toBeInTheDocument();
    expect(screen.getByText('Home')).toBeInTheDocument();
    expect(screen.getByText('AI Assistant')).toBeInTheDocument();
  });

  it('shows nav labels when sidebar is open', () => {
    mockUseSidebarContext.mockReturnValue({ isOpen: true, toggle: jest.fn() });
    render(<Sidebar />);

    expect(screen.getByText('Home')).toBeInTheDocument();
    expect(screen.getByText('API Catalog')).toBeInTheDocument();
    expect(screen.getByText('AI Assistant')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();
    expect(screen.getByText('Help')).toBeInTheDocument();
  });

  it('hides nav labels when sidebar is collapsed', () => {
    mockUseSidebarContext.mockReturnValue({ isOpen: false, toggle: jest.fn() });
    render(<Sidebar />);

    expect(screen.queryByText('Home')).not.toBeInTheDocument();
    expect(screen.queryByText('API Catalog')).not.toBeInTheDocument();
    expect(screen.queryByText('AI Assistant')).not.toBeInTheDocument();
    expect(screen.queryByText('Settings')).not.toBeInTheDocument();
    expect(screen.queryByText('Help')).not.toBeInTheDocument();
  });

  it('renders main navigation list', () => {
    render(<Sidebar />);

    expect(screen.getByRole('navigation', { name: /main navigation/i })).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: /secondary navigation/i })).toBeInTheDocument();
  });

  it('does NOT show admin section for non-admin users', () => {
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

  it('hides admin label but keeps Access Policies icon when collapsed and admin', () => {
    mockUseSidebarContext.mockReturnValue({ isOpen: false, toggle: jest.fn() });
    mockUseAuth.mockReturnValue(adminUser);
    render(<Sidebar />);
    // Label hidden when collapsed
    expect(screen.queryByText('Admin')).not.toBeInTheDocument();
    expect(screen.queryByText('Access Policies')).not.toBeInTheDocument();
    // But the nav list itself still exists
    expect(screen.getByRole('navigation', { name: /admin navigation/i })).toBeInTheDocument();
  });

  it('Access Policies link points to correct href', () => {
    mockUseAuth.mockReturnValue(adminUser);
    render(<Sidebar />);
    const link = screen.getByRole('link', { name: /access policies/i });
    expect(link).toHaveAttribute('href', '/admin/access-policies');
  });
});
