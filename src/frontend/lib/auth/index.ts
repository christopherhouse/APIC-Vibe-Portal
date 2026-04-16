/**
 * Public authentication API.
 */

export { default as AuthProvider } from './auth-provider';
export { default as AuthGuard } from './auth-guard';
export { useAuth, type AuthUser, type UseAuthReturn } from './use-auth';
export { useMsalConfig } from './msal-config-context';
export type { MsalConfig } from './msal-config';
