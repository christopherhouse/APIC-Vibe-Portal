import React from 'react';
import { render, screen, waitFor } from '../../../../__tests__/test-utils';
import '@testing-library/jest-dom';

// Mocks must be set up before imports
const mockUseAuth = jest.fn();
jest.mock('@/lib/auth/use-auth', () => ({
  useAuth: () => mockUseAuth(),
}));

const mockFetchPolicies = jest.fn();
jest.mock('@/lib/admin-api', () => ({
  fetchAccessPolicies: (...args: unknown[]) => mockFetchPolicies(...args),
  upsertAccessPolicy: jest.fn().mockResolvedValue({}),
  deleteAccessPolicy: jest.fn().mockResolvedValue(undefined),
  invalidatePolicyCache: jest.fn().mockResolvedValue(undefined),
}));

const mockFetchCatalogApis = jest.fn();
jest.mock('@/lib/catalog-api', () => ({
  fetchCatalogApis: (...args: unknown[]) => mockFetchCatalogApis(...args),
}));

import AccessPoliciesPage from '../page';

const adminUser = {
  isAuthenticated: true,
  user: { name: 'Admin', email: 'a@x.com', id: 'u2', roles: ['Portal.Admin'] },
};
const regularUser = {
  isAuthenticated: true,
  user: { name: 'Dev', email: 'd@x.com', id: 'u1', roles: ['Portal.User'] },
};

describe('AccessPoliciesPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFetchCatalogApis.mockResolvedValue({
      data: [
        { name: 'petstore-api', title: 'Petstore API' },
        { name: 'weather-api', title: 'Weather API' },
      ],
      meta: { page: 1, pageSize: 100, totalCount: 2, totalPages: 1 },
    });
  });

  it('shows access denied for non-admin users', async () => {
    mockUseAuth.mockReturnValue(regularUser);
    render(<AccessPoliciesPage />);
    // isLoading starts false for non-admins, so guard renders immediately
    await waitFor(() => {
      expect(screen.getByText(/Access Denied/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/Portal\.Admin/)).toBeInTheDocument();
  });

  it('renders page heading for admin user', async () => {
    mockUseAuth.mockReturnValue(adminUser);
    mockFetchPolicies.mockResolvedValue([]);
    render(<AccessPoliciesPage />);
    await waitFor(() => {
      expect(screen.getByText('API Access Policies')).toBeInTheDocument();
    });
  });

  it('shows empty state when no policies exist', async () => {
    mockUseAuth.mockReturnValue(adminUser);
    mockFetchPolicies.mockResolvedValue([]);
    render(<AccessPoliciesPage />);
    await waitFor(() => {
      expect(screen.getByTestId('policies-empty-state')).toBeInTheDocument();
    });
  });

  it('renders policy table rows when policies exist', async () => {
    mockUseAuth.mockReturnValue(adminUser);
    mockFetchPolicies.mockResolvedValue([
      {
        apiName: 'petstore-api',
        apiId: '',
        allowedGroups: ['grp-1'],
        isPublic: false,
        createdAt: '2026-01-01T00:00:00Z',
        updatedAt: '2026-01-02T00:00:00Z',
      },
    ]);
    render(<AccessPoliciesPage />);
    await waitFor(() => {
      expect(screen.getByTestId('policy-row-petstore-api')).toBeInTheDocument();
    });
  });

  it('shows New Policy and Refresh Cache buttons', async () => {
    mockUseAuth.mockReturnValue(adminUser);
    mockFetchPolicies.mockResolvedValue([]);
    render(<AccessPoliciesPage />);
    await waitFor(() => {
      expect(screen.getByTestId('add-policy-button')).toBeInTheDocument();
      expect(screen.getByTestId('refresh-cache-button')).toBeInTheDocument();
    });
  });

  it('shows load error when fetchAccessPolicies fails', async () => {
    mockUseAuth.mockReturnValue(adminUser);
    mockFetchPolicies.mockRejectedValue(new Error('Network error'));
    render(<AccessPoliciesPage />);
    await waitFor(() => {
      expect(screen.getByTestId('load-error')).toBeInTheDocument();
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });
  });
});
