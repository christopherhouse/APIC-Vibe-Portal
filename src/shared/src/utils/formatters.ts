/**
 * Format an ISO date string to a human-readable locale string.
 */
export function formatDate(isoDate: string, locale: string = 'en-US'): string {
  const date = new Date(isoDate);
  if (isNaN(date.getTime())) {
    return isoDate;
  }
  return date.toLocaleDateString(locale, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/**
 * Format an ISO date string to a relative time string (e.g., "2 hours ago").
 */
export function formatRelativeTime(isoDate: string): string {
  const date = new Date(isoDate);
  if (isNaN(date.getTime())) {
    return isoDate;
  }

  const now = Date.now();
  const diffMs = now - date.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSeconds < 60) return 'just now';
  if (diffMinutes < 60) return `${diffMinutes} minute${diffMinutes !== 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
  if (diffDays < 30) return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;

  return formatDate(isoDate);
}

const BYTE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB'] as const;

/**
 * Format bytes into a human-readable string (e.g., "1.5 MB").
 */
export function formatBytes(bytes: number, decimals: number = 1): string {
  if (bytes < 0) return '0 B';
  if (bytes === 0) return '0 B';

  const k = 1024;
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(k)), BYTE_UNITS.length - 1);
  const value = bytes / Math.pow(k, i);

  return `${value.toFixed(decimals)} ${BYTE_UNITS[i]}`;
}

/**
 * Normalize a URL by trimming whitespace, removing trailing slashes, and lowercasing the protocol/host.
 */
export function normalizeUrl(url: string): string {
  const trimmed = url.trim();
  if (!trimmed) return '';

  try {
    const parsed = new URL(trimmed);
    // Remove trailing slash from pathname unless it's the root
    if (parsed.pathname.length > 1 && parsed.pathname.endsWith('/')) {
      parsed.pathname = parsed.pathname.slice(0, -1);
    }
    return parsed.toString();
  } catch {
    // If parsing fails, just trim and remove trailing slash
    return trimmed.endsWith('/') ? trimmed.slice(0, -1) : trimmed;
  }
}

/**
 * Truncate a string to the specified max length, appending an ellipsis if truncated.
 */
export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - 1) + '…';
}
