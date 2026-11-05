import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  capitalize,
  formatBytes,
  formatDate,
  formatDateShort,
  formatPhone,
  formatRelative,
  formatTime,
  slugify,
  truncate,
} from './formatters';

afterEach(() => vi.useRealTimers());

describe('formatters', () => {
  it.each([null, undefined, ''])('handles missing dates %s', (value) => {
    expect(formatDate(value)).toBe('-');
    expect(formatDateShort(value)).toBe('-');
    expect(formatTime(value)).toBe('-');
    expect(formatRelative(value)).toBe('-');
  });

  it('formats dates without depending on the runner timezone', () => {
    expect(formatDate('2026-11-05T12:34:56')).toBe('05.11.2026 12:34');
    expect(formatDateShort('2026-11-05T12:34:56')).toBe('05.11.2026');
    expect(formatTime('2026-11-05T12:34:56')).toBe('12:34:56');
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-11-05T12:34:56'));
    expect(formatRelative('2026-11-05T12:34:56')).toBe('несколько секунд назад');
  });

  it.each([
    [0, '0 B'],
    [null, '0 B'],
    [512, '512 B'],
    [1024, '1.0 KB'],
    [10240, '10 KB'],
    [1024 ** 3, '1.0 GB'],
  ])('formats bytes %s', (value, result) => {
    expect(formatBytes(value as number | null)).toBe(result);
  });

  it('normalizes Unicode names and repeated separators', () => {
    expect(slugify('  Привет, Мир! -- Test  ')).toBe('привет-мир-test');
    expect(slugify('')).toBe('');
  });

  it('truncates only when needed', () => {
    expect(truncate('hello', 5)).toBe('hello');
    expect(truncate('hello world', 6)).toBe('hello…');
    expect(truncate('', 1)).toBe('');
  });

  it('capitalizes and formats phone numbers', () => {
    expect(capitalize('')).toBe('');
    expect(capitalize('привет')).toBe('Привет');
    expect(formatPhone('79991234567')).toBe('+7 (999) 123-45-67');
    expect(formatPhone('123')).toBe('123');
  });
});
