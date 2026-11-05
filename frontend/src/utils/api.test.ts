import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../api/generated';
import {
  extractErrorMessage,
  handleGlobalApiError,
  isConflict,
  isForbidden,
  isNotFound,
  isUnauthorized,
  isValidationError,
} from './api';

function apiError(status: number, body: unknown = null, statusText = 'Error'): ApiError {
  return new ApiError(
    { method: 'GET', url: '/test' },
    { url: '/test', ok: false, status, statusText, body },
    'API error'
  );
}

afterEach(() => vi.restoreAllMocks());

describe('API errors', () => {
  it.each([
    [401, isUnauthorized],
    [403, isForbidden],
    [404, isNotFound],
    [409, isConflict],
    [422, isValidationError],
  ] as const)('recognizes status %s', (status, predicate) => {
    expect(predicate(apiError(status))).toBe(true);
    expect(predicate(apiError(500))).toBe(false);
    expect(predicate(new Error('failure'))).toBe(false);
  });

  it('extracts structured validation details and handles unexpected responses', () => {
    expect(extractErrorMessage(apiError(400, { detail: 'bad request' }))).toBe('bad request');
    expect(extractErrorMessage(apiError(422, { detail: [{ msg: 'required' }, { field: 'email' }] }))).toBe(
      'required, {"field":"email"}'
    );
    expect(extractErrorMessage(apiError(500, 'unavailable'))).toBe('unavailable');
    expect(extractErrorMessage(apiError(500, ' '))).toBe('500 Error');
    expect(extractErrorMessage(new Error('network'))).toBe('network');
    expect(extractErrorMessage(null)).toBe('Не удалось выполнить запрос');
  });

  it('requests logout only on an unauthorized response', () => {
    const dispatch = vi.spyOn(window, 'dispatchEvent');
    handleGlobalApiError(apiError(403));
    expect(dispatch).not.toHaveBeenCalled();
    handleGlobalApiError(apiError(401));
    expect(dispatch).toHaveBeenCalledOnce();
    expect(dispatch.mock.calls[0][0].type).toBe('ms-admin:unauthorized');
  });
});
