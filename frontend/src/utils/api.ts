import { ApiError } from '../api/generated';

export function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}

export function extractErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const detail = error.body?.detail;

    if (typeof detail === 'string') {
      return detail;
    }

    if (Array.isArray(detail)) {
      return detail
        .map((item) => item?.msg ?? JSON.stringify(item))
        .filter(Boolean)
        .join(', ');
    }

    if (typeof error.body === 'string' && error.body.trim()) {
      return error.body;
    }

    return `${error.status} ${error.statusText}`.trim();
  }

  if (error instanceof Error) {
    return error.message;
  }

  return 'Не удалось выполнить запрос';
}

export function handleGlobalApiError(error: unknown): void {
  if (isUnauthorized(error)) {
    window.dispatchEvent(new Event('ms-admin:unauthorized'));
  }
}
