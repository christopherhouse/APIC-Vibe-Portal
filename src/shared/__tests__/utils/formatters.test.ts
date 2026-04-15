import {
  formatDate,
  formatRelativeTime,
  formatBytes,
  normalizeUrl,
  truncate,
} from '../../src/utils/formatters.js';

describe('formatters', () => {
  describe('formatDate', () => {
    it('formats a valid ISO date string', () => {
      const result = formatDate('2024-06-15T10:00:00Z', 'en-US');
      expect(result).toContain('Jun');
      expect(result).toContain('15');
      expect(result).toContain('2024');
    });

    it('returns the original string for invalid dates', () => {
      expect(formatDate('not-a-date')).toBe('not-a-date');
    });
  });

  describe('formatRelativeTime', () => {
    it('returns "just now" for very recent dates', () => {
      const now = new Date().toISOString();
      expect(formatRelativeTime(now)).toBe('just now');
    });

    it('returns minutes ago', () => {
      const date = new Date(Date.now() - 5 * 60 * 1000).toISOString();
      expect(formatRelativeTime(date)).toBe('5 minutes ago');
    });

    it('returns singular minute', () => {
      const date = new Date(Date.now() - 1 * 60 * 1000).toISOString();
      expect(formatRelativeTime(date)).toBe('1 minute ago');
    });

    it('returns hours ago', () => {
      const date = new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString();
      expect(formatRelativeTime(date)).toBe('3 hours ago');
    });

    it('returns singular hour', () => {
      const date = new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString();
      expect(formatRelativeTime(date)).toBe('1 hour ago');
    });

    it('returns days ago', () => {
      const date = new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString();
      expect(formatRelativeTime(date)).toBe('5 days ago');
    });

    it('returns singular day', () => {
      const date = new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString();
      expect(formatRelativeTime(date)).toBe('1 day ago');
    });

    it('falls back to formatDate for dates older than 30 days', () => {
      const date = new Date(Date.now() - 60 * 24 * 60 * 60 * 1000).toISOString();
      const result = formatRelativeTime(date);
      // Should return a formatted date, not "X days ago"
      expect(result).not.toContain('days ago');
    });

    it('returns the original string for invalid dates', () => {
      expect(formatRelativeTime('not-a-date')).toBe('not-a-date');
    });
  });

  describe('formatBytes', () => {
    it('formats 0 bytes', () => {
      expect(formatBytes(0)).toBe('0 B');
    });

    it('formats negative values as 0 B', () => {
      expect(formatBytes(-100)).toBe('0 B');
    });

    it('formats bytes', () => {
      expect(formatBytes(500)).toBe('500.0 B');
    });

    it('formats kilobytes', () => {
      expect(formatBytes(1024)).toBe('1.0 KB');
    });

    it('formats megabytes', () => {
      expect(formatBytes(1024 * 1024)).toBe('1.0 MB');
    });

    it('formats gigabytes', () => {
      expect(formatBytes(1024 * 1024 * 1024)).toBe('1.0 GB');
    });

    it('respects decimal precision', () => {
      expect(formatBytes(1536, 2)).toBe('1.50 KB');
    });
  });

  describe('normalizeUrl', () => {
    it('removes trailing slash', () => {
      expect(normalizeUrl('https://api.example.com/')).toBe('https://api.example.com/');
      // root slash stays as per URL normalization
    });

    it('removes trailing slash from paths', () => {
      expect(normalizeUrl('https://api.example.com/v1/')).toBe('https://api.example.com/v1');
    });

    it('trims whitespace', () => {
      expect(normalizeUrl('  https://api.example.com  ')).toBe('https://api.example.com/');
    });

    it('returns empty string for empty input', () => {
      expect(normalizeUrl('')).toBe('');
      expect(normalizeUrl('   ')).toBe('');
    });

    it('handles invalid URLs gracefully', () => {
      expect(normalizeUrl('not-a-url/')).toBe('not-a-url');
    });
  });

  describe('truncate', () => {
    it('does not truncate short strings', () => {
      expect(truncate('hello', 10)).toBe('hello');
    });

    it('truncates long strings with ellipsis', () => {
      expect(truncate('hello world', 6)).toBe('hello…');
    });

    it('handles exact length', () => {
      expect(truncate('hello', 5)).toBe('hello');
    });

    it('handles max length of 1', () => {
      expect(truncate('hello', 1)).toBe('…');
    });

    it('returns empty string for maxLength of 0', () => {
      expect(truncate('hello', 0)).toBe('');
    });

    it('returns empty string for negative maxLength', () => {
      expect(truncate('hello', -5)).toBe('');
    });
  });
});
