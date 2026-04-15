'use client';

/**
 * AuthGuard — protects routes that require authentication.
 *
 * While MSAL is processing a redirect it renders nothing.
 * If the user is not authenticated once processing completes, it triggers a login redirect.
 */

import React, { useEffect } from 'react';
import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';
import Typography from '@mui/material/Typography';
import { useAuth } from './use-auth';

interface AuthGuardProps {
  children: React.ReactNode;
  /** Optional list of roles the user must have to access the route. */
  requiredRoles?: string[];
}

export default function AuthGuard({ children, requiredRoles }: AuthGuardProps) {
  const { isAuthenticated, isLoading, login, user } = useAuth();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      login();
    }
  }, [isAuthenticated, isLoading, login]);

  if (isLoading) {
    return (
      <Box
        sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}
      >
        <CircularProgress />
      </Box>
    );
  }

  if (!isAuthenticated) {
    return (
      <Box
        sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}
      >
        <Typography variant="body1">Redirecting to login…</Typography>
      </Box>
    );
  }

  // Role check
  if (requiredRoles && requiredRoles.length > 0 && user) {
    const hasRole = requiredRoles.some((role) => user.roles.includes(role));
    if (!hasRole) {
      return (
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            height: '60vh',
            flexDirection: 'column',
            gap: 2,
          }}
        >
          <Typography variant="h5">Access Denied</Typography>
          <Typography variant="body1" color="text.secondary">
            You do not have the required role to view this page.
          </Typography>
        </Box>
      );
    }
  }

  return <>{children}</>;
}
