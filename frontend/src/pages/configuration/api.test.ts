import { afterEach, describe, expect, it, vi } from 'vitest';
import { OpenAPI } from '../../api/generated/core/OpenAPI';
import { configurationModules } from './api';

const original = { base: OpenAPI.BASE, token: OpenAPI.TOKEN };
afterEach(() => {
  vi.unstubAllGlobals();
  OpenAPI.BASE = original.base;
  OpenAPI.TOKEN = original.token;
});

describe('configuration API registry', () => {
  it.each(configurationModules)('uses the owned authenticated endpoints for $id', async (module) => {
    OpenAPI.BASE = 'http://localhost';
    OpenAPI.TOKEN = 'test-admin-token';
    const fetch = vi
      .fn()
      .mockImplementation(
        async () => new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } })
      );
    vi.stubGlobal('fetch', fetch);
    await module.read();
    await module.patch({ revision: 2, values: { key: 'value' } });
    await module.reset({ revision: 3, fields: ['key'] });
    const path = 'http://localhost/api/v1/public/' + module.id + '/configuration';
    expect(fetch.mock.calls.map(([url, options]) => [url, options.method])).toEqual([
      [path, 'GET'],
      [path, 'PATCH'],
      [path + '/reset', 'POST'],
    ]);
    for (const [, options] of fetch.mock.calls)
      expect(new Headers(options.headers).get('Authorization')).toBe('Bearer test-admin-token');
    expect(JSON.parse(fetch.mock.calls[1][1].body)).toEqual({ revision: 2, values: { key: 'value' } });
    expect(JSON.parse(fetch.mock.calls[2][1].body)).toEqual({ revision: 3, fields: ['key'] });
  });
});
