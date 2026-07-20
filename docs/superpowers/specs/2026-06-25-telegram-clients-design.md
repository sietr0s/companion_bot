# Модуль telegram_clients — Design Spec

**Дата:** 2026-06-25
**Статус:** Approved

## Цель

Модуль для управления Telegram-аккаунтами через Telethon (User API). Позволяет авторизовать аккаунты, получать чаты и сообщения, а также интегрируется с шиной сообщений для входящих/исходящих сообщений.

## Решения

| Решение | Выбор | Обоснование |
|---------|-------|-------------|
| Хранение сессий | SQLite session-файлы | Стандартный подход Telethon, простота |
| Входящие сообщения | Один топик для всех | Простота потребителей |
| Исходящие сообщения | Через шину (subscribe) | Полная интеграция с event-driven архитектурой |
| 2FA | С поддержкой | Полный флоу авторизации |
| История сообщений | On-demand из Telegram | Не дублируем данные, актуальность |
| Media | Массив объектов, без реализации отправки | Заложено на будущее через отдельный файловый сервис |

---

## Модель БД

### telegram_account

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| id | UUID | PK, default=uuid4 | Идентификатор аккаунта |
| auth_id | UUID | NOT NULL, INDEX | ID пользователя из модуля auth (без FK) |
| phone | VARCHAR(20) | NOT NULL | Номер телефона |
| session_file | VARCHAR(500) | NOT NULL | Путь к SQLite session-файлу |
| is_connected | BOOLEAN | DEFAULT FALSE | Подключён ли сейчас |
| first_name | VARCHAR(100) | NULLABLE | Имя из Telegram |
| last_name | VARCHAR(100) | NULLABLE | Фамилия из Telegram |
| username | VARCHAR(100) | NULLABLE | Username |
| telegram_id | BIGINT | NULLABLE | ID в Telegram (заполняется после авторизации) |
| created_at | TIMESTAMP | NOT NULL | Авто |
| updated_at | TIMESTAMP | NOT NULL | Авто |

---

## Структура модуля

```
src/modules/telegram_clients/
├── __init__.py
├── models.py              # TelegramAccount
├── schemas/
│   ├── __init__.py
│   ├── api.py             # PhoneRequest, CodeRequest, PasswordRequest, AccountRead, ChatRead, MessageRead, MediaItem
│   └── events.py          # TgMessageReceived, TgMessageSend, TgAccountConnected, TgAccountDisconnected
├── repository.py          # TelegramAccountRepository
├── client_manager.py      # TelegramClientManager — singleton управления Telethon-клиентами
├── service.py             # TelegramClientService
├── handlers.py            # Подписка на tg.message.send
└── router.py              # HTTP-роуты
```

---

## API-роуты

### Авторизация (3 шага)

| Метод | Путь | Описание | Тело | Ответ |
|-------|------|----------|------|-------|
| POST | `/telegram-clients/auth/phone` | Шаг 1: отправить номер | `{phone: "+79001234567"}` | `{account_id: UUID}` |
| POST | `/telegram-clients/auth/code` | Шаг 2: ввести SMS-код | `{account_id: UUID, code: "12345"}` | `{account_id: UUID, status: "connected"}` или `{status: "2fa_required"}` |
| POST | `/telegram-clients/auth/password` | Шаг 3: ввести 2FA пароль | `{account_id: UUID, password: "pass"}` | `{account_id: UUID, status: "connected"}` |

### Управление аккаунтами

| Метод | Путь | Описание | Ответ |
|-------|------|----------|-------|
| GET | `/telegram-clients/` | Все аккаунты пользователя | `list[AccountRead]` |
| DELETE | `/telegram-clients/{account_id}` | Удалить аккаунт | 204 |

### Чаты и сообщения

| Метод | Путь | Описание | Ответ |
|-------|------|----------|-------|
| GET | `/telegram-clients/{account_id}/chats` | Все чаты аккаунта | `list[ChatRead]` |
| GET | `/telegram-clients/{account_id}/chats/{chat_id}/messages` | Сообщения чата | `list[MessageRead]` |

Все роуты требуют JWT. `account_id` проверяется на принадлежность текущему пользователю.

---

## Шина сообщений

### Топики (BusTopics)

| Константа | Топик | Направление | Описание |
|-----------|-------|-------------|----------|
| `TG_MESSAGE_RECEIVED` | `telegram_clients.event.message.received` | Out (publish) | Входящее сообщение из Telegram |
| `TG_MESSAGE_SEND` | `telegram_clients.command.send_message` | In (subscribe) | Отправить сообщение через аккаунт |
| `TG_ACCOUNT_CONNECTED` | `tg.account.connected` | Out (publish) | Аккаунт подключён |
| `TG_ACCOUNT_DISCONNECTED` | `tg.account.disconnected` | Out (publish) | Аккаунт отключён |

### События

**TgMessageReceived** (publish):
```json
{
  "event_name": "telegram_clients.event.message.received",
  "account_id": "uuid",
  "chat_id": -1001234567890,
  "message_id": 42,
  "sender": {
    "sender_id": 123456789,
    "username": "vacancy_author",
    "first_name": "Иван",
    "last_name": "Иванов"
  },
  "text": "Привет!",
  "media": [
    {"type": "photo", "id": "AQADBAAT..."},
    {"type": "voice", "id": "AQADBgAT..."}
  ],
  "timestamp": "2026-06-25T10:00:00Z"
}
```

**TgMessageSend** (subscribe):
```json
{
  "event_name": "telegram_clients.command.send_message",
  "account_id": "uuid",
  "chat_id": -1001234567890,
  "text": "Ответ",
  "media": []
}
```

**TgAccountConnected** (publish):
```json
{
  "event_name": "tg.account.connected",
  "account_id": "uuid",
  "auth_id": "uuid",
  "phone": "+79001234567",
  "telegram_id": 123456789,
  "timestamp": "2026-06-25T10:00:00Z"
}
```

**TgAccountDisconnected** (publish):
```json
{
  "event_name": "tg.account.disconnected",
  "account_id": "uuid",
  "auth_id": "uuid",
  "reason": "manual | error | deleted",
  "timestamp": "2026-06-25T10:00:00Z"
}
```

### Обработчик отправки (handlers.py)

```python
@bus.subscribe(BusTopics.TG_MESSAGE_SEND)
async def handle_send_message(message: dict):
    account_id = message.get("account_id")
    chat_id = message.get("chat_id")
    text = message.get("text")
    # Получаем клиент через ClientManager и отправляем
```

---

## ClientManager — жизненный цикл

### Запуск (lifespan)

1. Загрузить из БД все `TelegramAccount` с `is_connected=True`
2. Для каждого — создать `TelegramClient(session_file)` и подключить
3. Зарегистрировать `on_new_message` → `publish(TG_MESSAGE_RECEIVED)`

### Авторизация

1. `/auth/phone` → создать `TelegramClient`, вызвать `send_code_request()`, сохранить аккаунт
2. `/auth/code` → `sign_in(code)`:
   - Успех → подключить, `is_connected=True`, publish `TG_ACCOUNT_CONNECTED`
   - `SessionPasswordNeededError` → вернуть `{status: "2fa_required"}`
3. `/auth/password` → `sign_in(password=...)` → подключить, publish `TG_ACCOUNT_CONNECTED`

### Удаление

1. Отключить клиент через ClientManager
2. Удалить session-файл с диска
3. Удалить запись из БД
4. Publish `TG_ACCOUNT_DISCONNECTED` с reason="deleted"

### Отправка через шину

1. `@bus.subscribe(TG_MESSAGE_SEND)` → получить клиент из manager → `client.send_message()`
2. В первой реализации — только текст, media не отправляется

---

## Media — реализация

**Статус:** ✅ Реализовано (2026-06-27)

### Входящие сообщения

При получении сообщения с медиа:

1. `TelegramClientManager.download_media()` — скачать bytes из Telegram
2. `upload_media_to_storage()` — POST /internal/media/upload
3. Сохранить `file_id` из ответа в `TgMessageReceived.media[].file_id`

**Формат media в событии:**

```json
{
  "media": [
    {
      "type": "photo",
      "id": "AQADBAAT...",
      "file_id": "550e8400-e29b-41d4-a716-446655440000"
    }
  ]
}
```

**Преимущества:**
- Подписчики получают готовый `file_id` — могут скачать через `/internal/media/{id}`
- Telegram-модуль не хранит бинарные данные
- Файлы независимы — переиспользование в других контекстах

---

## Конфигурация

Добавить в `Settings` (`core/config.py`):

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `TG_API_ID` | — | API ID из my.telegram.org |
| `TG_API_HASH` | — | API Hash из my.telegram.org |
| `TG_SESSION_DIR` | `sessions/` | Директория для session-файлов |

---

## Зависимости

Добавить в `requirements.txt`:
- `telethon>=1.34.0`

---

## Интеграция с существующим проектом

1. Добавить топики в `BusTopics`
2. Добавить фабрики в `dependencies.py`
3. Подключить роутер в `main.py`
4. Зарегистрировать обработчики в `main.py`
5. Инициализировать `TelegramClientManager` в `lifespan`
6. Добавить зависимость `telethon` в `requirements.txt`
