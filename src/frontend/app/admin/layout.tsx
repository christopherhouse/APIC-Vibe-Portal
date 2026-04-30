'use client';

/**
 * Admin section layout.
 *
 * Wraps every `/admin/**` route in an `AuthGuard` requiring `Portal.Admin`.
 * Individual admin pages still perform their own role checks defensively
 * (belt-and-braces) but this layout ensures we never accidentally ship an
 * admin page that is missing the guard.
 */

import React from 'react';
import AuthGuard from '@/lib/auth/auth-guard';

const ADMIN_ROLE = 'Portal.Admin';

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return <AuthGuard requiredRoles={[ADMIN_ROLE]}>{children}</AuthGuard>;
}
