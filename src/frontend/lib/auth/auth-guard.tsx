'use client';

/**
 * AuthGuard component for protecting routes.
 *
 * Wraps children and only renders them when the user is authenticated.
 * Redirects unauthenticated users to login automatically.
 */

import { type ReactNode, useEffect } from 'react';

import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';
import Typography from '@mui/material/Typography';

import { useAuth } from './use-auth';

interface AuthGuardProps {
  /** The content to render when authenticated. */
  children: ReactNode;
  /** Optional roles required to access this content. */
  requiredRoles?: string[];
  /** Fallback content when access is denied (insufficient roles). */
  accessDeniedFallback?: ReactNode;
}

/**
 * Protects child content behind authentication.
 *
 * - Shows a loading spinner during auth initialization
 * - Automatically triggers login for unauthenticated users
 * - Optionally checks for required roles
 */
export default function AuthGuard({
  children,
  requiredRoles,
  accessDeniedFallback,
}: AuthGuardProps) {
  const { isAuthenticated, isLoading, user, login } = useAuth();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      void login();
    }
  }, [isLoading, isAuthenticated, login]);

  // Still loading auth state
  if (isLoading) {
    return (
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '50vh',
          gap: 2,
        }}
      >
        <CircularProgress />
        <Typography variant="body2" color="text.secondary">
          Checking authentication…
        </Typography>
      </Box>
    );
  }

  // Not authenticated — login redirect is in progress
  if (!isAuthenticated) {
    return (
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '50vh',
          gap: 2,
        }}
      >
        <CircularProgress />
        <Typography variant="body2" color="text.secondary">
          Redirecting to login…
        </Typography>
      </Box>
    );
  }

  // Check roles if required
  if (requiredRoles && requiredRoles.length > 0 && user) {
    const hasRequiredRole = requiredRoles.some((role) => user.roles.includes(role));
    if (!hasRequiredRole) {
      return (
        accessDeniedFallback ?? (
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              minHeight: '50vh',
              gap: 2,
            }}
          >
            <Typography variant="h5" color="error">
              Access Denied
            </Typography>
            <Typography variant="body1" color="text.secondary">
              You do not have the required permissions to access this page.
            </Typography>
          </Box>
        )
      );
    }
  }

  return <>{children}</>;
}
