import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../../api/generated/core/ApiError';
import { ConfigurationService } from '../../api/generated/services/ConfigurationService';
import type { ConfigRead } from '../../api/generated/models/ConfigRead';
import { ConfigurationPage } from './ConfigurationPage';

window.matchMedia = vi
  .fn()
  .mockImplementation(() => ({ matches: false, addListener: vi.fn(), removeListener: vi.fn() }));

const initial: ConfigRead = {
  revision: 3,
  values: { BATCH_MAX_SIZE: 20, BATCH_IDLE_SECONDS: 2 },
  overrides: { BATCH_MAX_SIZE: 20 },
  sources: { BATCH_MAX_SIZE: 'database', BATCH_IDLE_SECONDS: 'default' },
  obsolete_keys: [],
  field_schema: {
    properties: {
      BATCH_MAX_SIZE: { type: 'integer', minimum: 1 },
      BATCH_IDLE_SECONDS: { type: 'number', exclusiveMinimum: 0 },
    },
  },
  apply_mode: 'restart',
};

function apiError(status: number, detail: string) {
  return new ApiError(
    { method: 'PATCH', url: '/' },
    { status, statusText: 'Error', body: { detail }, url: '/', ok: false },
    detail
  );
}

function openPage(module = 'batching') {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/configuration?module=' + module]}>
        <ConfigurationPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
  return client;
}

beforeEach(() => {
  vi.spyOn(ConfigurationService, 'readApiV1PublicBatchingConfigurationGet').mockResolvedValue(structuredClone(initial));
});
afterEach(() => vi.restoreAllMocks());

describe('module configuration', () => {
  it('saves only changed fields with the displayed revision and announces restart', async () => {
    const patch = vi
      .spyOn(ConfigurationService, 'patchApiV1PublicBatchingConfigurationPatch')
      .mockResolvedValue({ ...initial, revision: 4, values: { ...initial.values, BATCH_MAX_SIZE: 7 } });
    openPage();
    const input = await screen.findByLabelText('BATCH_MAX_SIZE');
    expect(screen.getByText('БД')).toBeTruthy();
    expect(screen.getByText('По умолчанию')).toBeTruthy();
    expect(screen.getByText('Ревизия 3 · Значения для следующего запуска')).toBeTruthy();
    fireEvent.change(input, { target: { value: '7' } });
    fireEvent.click(screen.getByRole('button', { name: 'Сохранить изменения' }));
    await waitFor(() => expect(patch).toHaveBeenCalledWith({ revision: 3, values: { BATCH_MAX_SIZE: 7 } }));
    expect(await screen.findByText('Конфигурация сохранена. Требуется перезапуск.')).toBeTruthy();
    expect(screen.getByText('Ревизия 4 · Значения для следующего запуска')).toBeTruthy();
  });

  it('validates before sending and lets the user discard edits', async () => {
    const patch = vi.spyOn(ConfigurationService, 'patchApiV1PublicBatchingConfigurationPatch');
    openPage();
    const input = await screen.findByLabelText('BATCH_MAX_SIZE');
    fireEvent.change(input, { target: { value: '0' } });
    fireEvent.click(screen.getByRole('button', { name: 'Сохранить изменения' }));
    expect(await screen.findByText('Минимум: 1')).toBeTruthy();
    expect(patch).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Отменить изменения' }));
    expect((screen.getByLabelText('BATCH_MAX_SIZE') as HTMLInputElement).value).toBe('20');
  });

  it('requires confirmation to reset an override using the current revision', async () => {
    const reset = vi
      .spyOn(ConfigurationService, 'resetApiV1PublicBatchingConfigurationResetPost')
      .mockResolvedValue({ ...initial, revision: 4, overrides: {} });
    openPage();
    fireEvent.click(await screen.findByRole('button', { name: 'Сбросить BATCH_MAX_SIZE' }));
    expect(reset).not.toHaveBeenCalled();
    fireEvent.click(await screen.findByRole('button', { name: /^Сбросить$/ }));
    await waitFor(() => expect(reset).toHaveBeenCalledWith({ revision: 3, fields: ['BATCH_MAX_SIZE'] }));
  });

  it('preserves edits on conflict and blocks resubmission until explicit reload', async () => {
    const patch = vi
      .spyOn(ConfigurationService, 'patchApiV1PublicBatchingConfigurationPatch')
      .mockRejectedValue(apiError(409, 'conflict'));
    openPage();
    fireEvent.change(await screen.findByLabelText('BATCH_MAX_SIZE'), { target: { value: '9' } });
    fireEvent.click(screen.getByRole('button', { name: 'Сохранить изменения' }));
    expect(await screen.findByText('Конфигурация изменена другим редактором')).toBeTruthy();
    expect((screen.getByLabelText('BATCH_MAX_SIZE') as HTMLInputElement).value).toBe('9');
    expect((screen.getByRole('button', { name: 'Сохранить изменения' }) as HTMLButtonElement).disabled).toBe(true);
    vi.mocked(ConfigurationService.readApiV1PublicBatchingConfigurationGet).mockResolvedValue({
      ...initial,
      revision: 5,
      values: { ...initial.values, BATCH_MAX_SIZE: 11 },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Перечитать' }));
    const dialog = await screen.findByRole('dialog');
    fireEvent.click(within(dialog).getByRole('button', { name: 'Перечитать' }));
    expect(await screen.findByText('Ревизия 5 · Значения для следующего запуска')).toBeTruthy();
    expect((screen.getByLabelText('BATCH_MAX_SIZE') as HTMLInputElement).value).toBe('11');
    expect(patch).toHaveBeenCalledTimes(1);
  });

  it('keeps the form on server validation failure', async () => {
    vi.spyOn(ConfigurationService, 'patchApiV1PublicBatchingConfigurationPatch').mockRejectedValue(
      apiError(422, 'Invalid combination')
    );
    openPage();
    fireEvent.change(await screen.findByLabelText('BATCH_MAX_SIZE'), { target: { value: '9' } });
    fireEvent.click(screen.getByRole('button', { name: 'Сохранить изменения' }));
    expect(await screen.findByText('Invalid combination')).toBeTruthy();
    expect((screen.getByLabelText('BATCH_MAX_SIZE') as HTMLInputElement).value).toBe('9');
    expect((screen.getByRole('button', { name: 'Сохранить изменения' }) as HTMLButtonElement).disabled).toBe(false);
  });

  it('shows an admin permission error without an editable form', async () => {
    vi.mocked(ConfigurationService.readApiV1PublicBatchingConfigurationGet).mockRejectedValue(
      apiError(403, 'Forbidden')
    );
    openPage();
    expect(await screen.findByText('Для настройки модулей нужны права администратора')).toBeTruthy();
    expect(screen.queryByLabelText('BATCH_MAX_SIZE')).toBeNull();
  });

  it('shows empty modules and does not invent settings', async () => {
    vi.spyOn(ConfigurationService, 'readApiV1PublicUsersConfigurationGet').mockResolvedValue({
      ...initial,
      values: {},
      overrides: {},
      sources: {},
      field_schema: { properties: {} },
    });
    openPage('users');
    expect(await screen.findByText('У этого модуля пока нет изменяемых параметров')).toBeTruthy();
    expect((screen.getByRole('button', { name: 'Сохранить изменения' }) as HTMLButtonElement).disabled).toBe(true);
  });

  it('renders enums, booleans and multiline text from the schema', async () => {
    vi.spyOn(ConfigurationService, 'readApiV1PublicLlmConfigurationGet').mockResolvedValue({
      ...initial,
      values: { PROVIDER: 'stub', ENABLED: false, TEMPLATE: 'hello' },
      overrides: {},
      field_schema: {
        properties: {
          PROVIDER: { type: 'string', enum: ['stub', 'mistral'] },
          ENABLED: { type: 'boolean' },
          TEMPLATE: { type: 'string' },
        },
      },
    });
    const patch = vi
      .spyOn(ConfigurationService, 'patchApiV1PublicLlmConfigurationPatch')
      .mockResolvedValue({ ...initial, revision: 4 });
    openPage('llm');
    const toggle = await screen.findByLabelText('ENABLED');
    fireEvent.click(toggle);
    fireEvent.change(screen.getByLabelText('TEMPLATE'), { target: { value: 'line 1\nline 2' } });
    fireEvent.click(screen.getByRole('button', { name: 'Сохранить изменения' }));
    await waitFor(() =>
      expect(patch).toHaveBeenCalledWith({ revision: 3, values: { ENABLED: true, TEMPLATE: 'line 1\nline 2' } })
    );
  });
});

it('warns before switching a module with unsaved changes and keeps edits on cancel', async () => {
  openPage();
  fireEvent.change(await screen.findByLabelText('BATCH_MAX_SIZE'), { target: { value: '8' } });
  fireEvent.keyDown(screen.getByRole('combobox', { name: 'Модуль' }), {
    key: 'ArrowDown',
    code: 'ArrowDown',
    keyCode: 40,
    which: 40,
  });
  fireEvent.click(await screen.findByText('Users', { exact: true }));
  const dialog = await screen.findByRole('dialog');
  fireEvent.click(within(dialog).getByRole('button', { name: 'Остаться' }));
  expect((screen.getByLabelText('BATCH_MAX_SIZE') as HTMLInputElement).value).toBe('8');
});

it('resets all overrides, including obsolete keys, as a single revisioned request', async () => {
  vi.mocked(ConfigurationService.readApiV1PublicBatchingConfigurationGet).mockResolvedValue({
    ...initial,
    overrides: { BATCH_MAX_SIZE: 20, REMOVED_SETTING: 'old' },
    obsolete_keys: ['REMOVED_SETTING'],
  });
  const reset = vi
    .spyOn(ConfigurationService, 'resetApiV1PublicBatchingConfigurationResetPost')
    .mockResolvedValue({ ...initial, revision: 4, overrides: {} });
  openPage();
  expect(await screen.findByText('Устаревшие переопределения')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Сбросить все переопределения' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Сбросить всё' }));
  await waitFor(() =>
    expect(reset).toHaveBeenCalledWith({ revision: 3, fields: ['BATCH_MAX_SIZE', 'REMOVED_SETTING'] })
  );
});

it('retries a failed read without issuing writes', async () => {
  vi.mocked(ConfigurationService.readApiV1PublicBatchingConfigurationGet).mockRejectedValueOnce(new Error('Offline'));
  openPage();
  expect(await screen.findByText('Не удалось загрузить конфигурацию')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Повторить' }));
  expect(await screen.findByLabelText('BATCH_MAX_SIZE')).toBeTruthy();
});
