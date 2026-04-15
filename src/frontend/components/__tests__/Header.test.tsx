import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock useAuth
const mockLogin = jest.fn();
const mockLogout = jest.fn();
const mockUseAuth = jest.fn();

jest.mock('@/lib/auth/use-auth', () => ({
  useAuth: () => mockUseAuth(),
}));

import Header from '../layout/Header';

describe('Header Auth UI', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('shows Sign in button when not authenticated', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
      user: null,
      login: mockLogin,
      logout: mockLogout,
    });

    render(<Header />);
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('calls login when Sign in is clicked', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
      user: null,
      login: mockLogin,
      logout: mockLogout,
    });

    render(<Header />);
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));
    expect(mockLogin).toHaveBeenCalled();
  });

  it('shows user avatar when authenticated', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: { name: 'John Doe', email: 'john@example.com', id: '1', roles: ['Portal.User'] },
      login: mockLogin,
      logout: mockLogout,
    });

    render(<Header />);
    expect(screen.queryByRole('button', { name: /sign in/i })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /user menu/i })).toBeInTheDocument();
  });

  it('shows user menu with name and sign out on avatar click', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: { name: 'John Doe', email: 'john@example.com', id: '1', roles: ['Portal.User'] },
      login: mockLogin,
      logout: mockLogout,
    });

    render(<Header />);
    fireEvent.click(screen.getByRole('button', { name: /user menu/i }));

    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('john@example.com')).toBeInTheDocument();
    expect(screen.getByText('Sign out')).toBeInTheDocument();
  });

  it('calls logout when Sign out is clicked', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: { name: 'John Doe', email: 'john@example.com', id: '1', roles: ['Portal.User'] },
      login: mockLogin,
      logout: mockLogout,
    });

    render(<Header />);
    fireEvent.click(screen.getByRole('button', { name: /user menu/i }));
    fireEvent.click(screen.getByText('Sign out'));
    expect(mockLogout).toHaveBeenCalled();
  });

  it('shows nothing for user area while loading', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: true,
      user: null,
      login: mockLogin,
      logout: mockLogout,
    });

    render(<Header />);
    expect(screen.queryByRole('button', { name: /sign in/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /user menu/i })).not.toBeInTheDocument();
  });

  it('always shows the APIC Vibe Portal title', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
      user: null,
      login: mockLogin,
      logout: mockLogout,
    });

    render(<Header />);
    expect(screen.getByText('APIC Vibe Portal')).toBeInTheDocument();
  });
});
