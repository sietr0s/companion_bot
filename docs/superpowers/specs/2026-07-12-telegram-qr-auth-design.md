# Telegram QR-авторизация

**Дата**: 2026-07-12
**Статус**: draft

## Цель

Добавить альтернативный способ авторизации Telegram-аккаунта через QR-код (без SMS). Пользователь выбирает метод на фронте, сканирует QR через приложение Telegram, и аккаунт подключается автоматически.

## API

Новые роуты добавляются в `src/modules/telegram_clients/routers/public.py`:

| Метод | Путь | Назначение |
|-------|------|------------|
| `POST` | `/api/v1/public/telegram/auth/qr` | Старт QR-сессии |
| `GET` | `/api/v1/public/telegram/auth/qr/{account_id}/status` | Статус QR-сессии |
| `DELETE` | `/api/v1/public/telegram/auth/qr/{account_id}` | Отмена QR-сессии |

### `POST /auth/qr`

- Генерирует `account_id` (UUID)
- Создаёт временный `TelegramClient` через `client_manager.start_qr_login(account_id)`
- Запускает фоновый `asyncio.Task` — `client.qr_login().wait()`
- Запись в БД **не создаётся** на этом этапе
- Возвращает `{account_id, qr_url, expires_at}`

### `GET /auth/qr/{account_id}/status`

- Читает in-memory статус из `client_manager.get_qr_status(account_id)`
- Возвращает `{status: "pending"|"connected"|"expired"|"error", message: ...}`

### `DELETE /auth/qr/{account_id}`

- Отменяет фоновый `asyncio.Task`
- Отключает временный клиент
- Чистит in-memory данные

### Финализация после connected

При статусе `connected` фронт вызывает существующий механизм: сервис создаёт запись в БД (поля заполняются из `client.get_me()`), публикует событие `TgAccountConnected`.

## Схемы (Pydantic)

Добавляются в `src/modules/telegram_clients/schemas/public/auth.py`:

```python
class QrStartResponse(BaseModel):
    account_id: uuid.UUID
    qr_url: str
    expires_at: float | None

class QrStatusResponse(BaseModel):
    status: str  # "pending" | "connected" | "expired" | "error"
    message: str | None = None
```

## Константы

Добавляются в `src/modules/telegram_clients/constants.py`:

```python
class QrAuthStatus(StrEnum):
    PENDING = "pending"
    CONNECTED = "connected"
    EXPIRED = "expired"
    ERROR = "error"
```

## ClientManager

Новые поля и методы в `TelegramClientManager`:

### In-memory структуры

- `_qr_sessions: dict[uuid.UUID, dict]` — статус QR-сессии
- `_qr_tasks: dict[uuid.UUID, asyncio.Task]` — фоновые задачи `qr.wait()`

### Методы

- `async start_qr_login(account_id) -> QrStartData`
  - Создаёт временный клиент, вызывает `client.qr_login()`
  - Запускает `asyncio.create_task(_qr_wait_worker(account_id, client, qr))`
  - Возвращает `{qr_url, expires_at}`

- `async _qr_wait_worker(account_id, client, qr)`
  - Вызывает `await qr.wait()`
  - Успех → статус `connected`, `_register_message_handler`
  - Таймаут → статус `expired`
  - Исключение → статус `error`

- `def get_qr_status(account_id) -> dict` — чтение статуса из `_qr_sessions`

- `async cancel_qr_login(account_id) -> None` — отмена задачи, отключение клиента, очистка данных

- `async complete_qr_login(account_id) -> dict` — `get_me()` на уже подключённом клиенте

### Статус клиента

Временный клиент хранится в `_clients[account_id]`. После успешного QR-сканирования он уже зарегистрирован через `_register_message_handler` и становится полноценным.

## Service

Новые методы в `TelegramClientService`:

- `async start_qr_auth(session, auth_id) -> QrStartResponse` — делегирует в `client_manager.start_qr_login()`
- `async get_qr_status(account_id) -> QrStatusResponse` — делегирует в `client_manager.get_qr_status()`
- `async complete_qr_auth(session, auth_id, account_id) -> AccountRead`
  - Вызывает `client_manager.complete_qr_login(account_id)`
  - Создаёт `TelegramAccount` в БД (phone заполняется из `get_me()` если доступен, иначе пустой строкой)
  - Публикует `TgAccountConnected`
- `async cancel_qr_auth(account_id) -> None` — делегирует в `client_manager.cancel_qr_login()`

## Frontend

Изменения в `TelegramPage.tsx`:

- **Переключатель метода**: `Radio.Group` («SMS | QR») над блоком авторизации
- **QR-режим**:
  - Скрывается старый wizard/Steps
  - `POST /auth/qr` → получает `qr_url`
  - Рендерит QR-код через `qrcode.react` (`<QRCodeSVG value={qrUrl} />`)
  - Polling: `setInterval` 3 сек → `GET /auth/qr/{id}/status`
  - Статус `connected` → авто-вызов финализации, инвалидация списка аккаунтов
  - Кнопка «Отмена» → `DELETE /auth/qr/{id}`, сброс состояния
  - Показ статуса: «Ожидание сканирования...», «Подключено!», «QR истёк — попробуйте снова», «Ошибка»
- **SMS-режим**: существующее поведение без изменений

Новая зависимость: `qrcode.react` (только рендеринг QR, не генерация).

## Документация

Обновить `docs/modules/telegram_clients.md`:
- Добавить раздел QR-авторизации
- Добавить новые роуты в таблицу HTTP API
- Обновить примеры

## Что НЕ делаем

- Не добавляем миграции БД (QR-сессия только в памяти)
- Не меняем модель `TelegramAccount` (phone остаётся `nullable=False` — заполняется из `get_me()` при QR)
- Не добавляем `qrcode` (Python) в requirements.txt — QR генерируется на фронте
- Не трогаем существующие SMS-роуты
