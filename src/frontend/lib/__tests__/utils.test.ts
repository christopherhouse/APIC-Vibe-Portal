import { formatDate, truncate, debounce, cn } from '../utils';

describe('formatDate', () => {
  it('formats a Date object to en-US by default', () => {
    const result = formatDate(new Date('2026-04-15'));
    expect(result).toBe('April 15, 2026');
  });

  it('formats a date string', () => {
    const result = formatDate('2025-01-01');
    expect(result).toBe('January 1, 2025');
  });

  it('accepts a custom locale', () => {
    const result = formatDate('2026-06-01', 'en-GB');
    expect(result).toBe('1 June 2026');
  });
});

describe('truncate', () => {
  it('returns the original string if shorter than maxLength', () => {
    expect(truncate('hello', 10)).toBe('hello');
  });

  it('returns the original string if exactly at maxLength', () => {
    expect(truncate('hello', 5)).toBe('hello');
  });

  it('truncates with ellipsis if longer than maxLength', () => {
    expect(truncate('hello world', 5)).toBe('hello…');
  });

  it('handles empty strings', () => {
    expect(truncate('', 5)).toBe('');
  });

  it('handles maxLength of 0', () => {
    expect(truncate('hello', 0)).toBe('…');
  });
});

describe('debounce', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('delays execution by the specified delay', () => {
    const fn = jest.fn();
    const debounced = debounce(fn, 300);

    debounced();
    expect(fn).not.toHaveBeenCalled();

    jest.advanceTimersByTime(300);
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it('cancels pending calls when invoked again', () => {
    const fn = jest.fn();
    const debounced = debounce(fn, 300);

    debounced();
    jest.advanceTimersByTime(100);
    debounced();
    jest.advanceTimersByTime(300);

    expect(fn).toHaveBeenCalledTimes(1);
  });

  it('forwards arguments to the debounced function', () => {
    const fn = jest.fn();
    const debounced = debounce(fn, 100);

    debounced('a', 'b');
    jest.advanceTimersByTime(100);

    expect(fn).toHaveBeenCalledWith('a', 'b');
  });
});

describe('cn', () => {
  it('combines multiple class names', () => {
    expect(cn('foo', 'bar', 'baz')).toBe('foo bar baz');
  });

  it('filters out undefined values', () => {
    expect(cn('foo', undefined, 'bar')).toBe('foo bar');
  });

  it('filters out null values', () => {
    expect(cn('foo', null, 'bar')).toBe('foo bar');
  });

  it('filters out false values', () => {
    expect(cn('foo', false, 'bar')).toBe('foo bar');
  });

  it('returns empty string for no valid classes', () => {
    expect(cn(undefined, null, false)).toBe('');
  });

  it('returns empty string for no arguments', () => {
    expect(cn()).toBe('');
  });
});
