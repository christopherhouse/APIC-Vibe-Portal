import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

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

describe('Sidebar', () => {
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
    mockUseSidebarContext.mockReturnValue({ isOpen: true, toggle: jest.fn() });
    render(<Sidebar />);

    expect(screen.getByRole('navigation', { name: /main navigation/i })).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: /secondary navigation/i })).toBeInTheDocument();
  });
});
