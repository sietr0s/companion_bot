import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { OpenAPI } from '../api/generated';
import { AuthProvider, useAuth } from './AuthContext';

beforeEach(() => window.localStorage.clear());
afterEach(() => vi.restoreAllMocks());

describe('authentication state', () => {
  it('starts logged out and persists login/logout consistently', () => {
    const { result } = renderHook(useAuth, { wrapper: AuthProvider });
    expect(result.current.isAuthenticated).toBe(false);
    act(() => result.current.setToken('test-only-token'));
    expect(result.current.isAuthenticated).toBe(true);
    expect(window.localStorage.getItem('ms_starter_admin_token')).toBe('test-only-token');
    act(() => result.current.logout());
    expect(result.current.token).toBeNull();
    expect(window.localStorage.getItem('ms_starter_admin_token')).toBeNull();
  });

  it('restores the stored token before child API requests', async () => {
    window.localStorage.setItem('ms_starter_admin_token', 'stored-test-token');
    const { result } = renderHook(useAuth, { wrapper: AuthProvider });
    expect(result.current.token).toBe('stored-test-token');
    const resolve = OpenAPI.TOKEN;
    if (typeof resolve !== 'function') throw new Error('Expected a dynamic token resolver');
    expect(await resolve({ method: 'GET', url: '/test' })).toBe('stored-test-token');
    act(() => result.current.logout());
    expect(await resolve({ method: 'GET', url: '/test' })).toBe('');
  });

  it('clears authentication on 401 and removes listeners when unmounted', () => {
    const remove = vi.spyOn(window, 'removeEventListener');
    const { result, unmount } = renderHook(useAuth, { wrapper: AuthProvider });
    act(() => result.current.setToken('test-only-token'));
    act(() => window.dispatchEvent(new Event('ms-admin:unauthorized')));
    expect(result.current.isAuthenticated).toBe(false);
    expect(window.localStorage.getItem('ms_starter_admin_token')).toBeNull();
    unmount();
    expect(remove).toHaveBeenCalledWith('ms-admin:unauthorized', expect.any(Function));
  });

  it('reports a missing provider explicitly', () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    expect(() => renderHook(useAuth)).toThrow('useAuth must be used inside AuthProvider');
  });
});
