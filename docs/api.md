# API документация

## Общая информация

- Базовый URL: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- Формат тела запроса/ответа: `application/json`
- Авторизация: `Bearer <JWT-токен>` в заголовке `Authorization`

## Версионирование API

Все публичные endpoint'ы доступны через префикс `/api/v1/public/`. Это позволяет:
- Корректно версионировать API
- Вносить breaking changes в будущих версиях (v2, v3)
- Поддерживать обратную совместимость

**Примеры:**
- `GET /api/v1/public/users/me` — получение профиля
- `POST /api/v1/public/auth/login` — вход
- `POST /api/v1/public/media/upload` — загрузка файла

Internal API (для внутреннего использования) остаются без версионирования:
- `GET /internal/auth/{id}` — внутренний вызов
- `POST /internal/users/filter` — внутренний вызов

---

## Auth

### POST /api/v1/public/auth/register

Регистрация нового пользователя. Создаёт учётную запись авторизации и возвращает JWT-токен.

Поддерживает регистрацию по **email**, **телефону** ИЛИ **telegram username**.

Профиль пользователя создаётся **отдельным запросом** `POST /api/v1/public/users/`.

**Тело запроса:**

```json
{
  "identifier": "user@example.com",
  "identifier_type": "email",
  "password": "securepassword"
}
```

Или для телефона:

```json
{
  "identifier": "+79001234567",
  "identifier_type": "phone",
  "password": "securepassword"
}
```

Или для telegram:

```json
{
  "identifier": "@username",
  "identifier_type": "telegram",
  "password": "securepassword"
}
```

| Поле | Тип | Валидация |
|------|-----|-----------|
| identifier | str | Обязательное, уникальное. Email, телефон или telegram username |
| identifier_type | Literal["email", "phone", "telegram"] | Обязательное. Тип идентификатора |
| password | str | Минимум 8 символов |

**Валидация identifier:**
- **email**: Должен содержать `@` и точку после `@`
- **phone**: Должен начинаться с `+` или `8`, после префикса — только цифры (формат E.164: `+79001234567` или `89001234567`)
- **telegram**: 5-32 символа, буквы, цифры, подчеркивание. Может начинаться с `@`. Не может начинаться с цифры (например, `@validuser`, `user_name123`)

**Ответ 201:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Ошибки:**

| Статус | Описание |
|--------|----------|
| 409 | Пользователь с таким identifier уже существует |
| 422 | Неверный формат identifier (валидация Pydantic) |

---

### POST /api/v1/public/auth/login

Авторизация пользователя. Проверяет identifier (email, телефон или telegram username) и пароль, возвращает JWT-токен.

**Тело запроса:**

```json
{
  "identifier": "user@example.com",
  "password": "securepassword"
}
```

Или для телефона:

```json
{
  "identifier": "+79001234567",
  "password": "securepassword"
}
```

Или для telegram:

```json
{
  "identifier": "@username",
  "password": "securepassword"
}
```

| Поле | Тип | Валидация |
|------|-----|-----------|
| identifier | str | Обязательное. Email, телефон или telegram username |
| password | str | Обязательное |

**Ответ 200:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Ошибки:**

| Статус | Описание |
|--------|----------|
| 401 | Неверный идентификатор или пароль |
| 422 | Неверный формат identifier (валидация Pydantic) |

---

## Users

> Все эндпоинты требуют авторизацию: `Authorization: Bearer <token>`

### POST /api/v1/public/users/

Создание профиля пользователя. `auth_id` берётся из JWT-токена, а не из тела запроса.

**Тело запроса:**

```json
{
  "first_name": "Иван",
  "last_name": "Иванов",
  "avatar_url": "https://example.com/avatar.jpg",
  "bio": "Разработчик"
}
```

| Поле | Тип | Валидация |
|------|-----|-----------|
| first_name | str \| null | Макс. 100 символов |
| last_name | str \| null | Макс. 100 символов |
| avatar_url | str \| null | Макс. 500 символов |
| bio | str \| null | Без ограничения |

Все поля опциональны.

**Ответ 201:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "auth_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "first_name": "Иван",
  "last_name": "Иванов",
  "avatar_url": "https://example.com/avatar.jpg",
  "bio": "Разработчик",
  "created_at": "2026-06-25T10:00:00Z",
  "updated_at": "2026-06-25T10:00:00Z"
}
```

**Ошибки:**

| Статус | Описание |
|--------|----------|
| 409 | Профиль для данного пользователя уже существует |

---

### GET /api/v1/public/users/me

Получение профиля текущего пользователя.

**Ответ 200:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "auth_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "first_name": "Иван",
  "last_name": "Иванов",
  "avatar_url": null,
  "bio": null,
  "created_at": "2026-06-25T10:00:00Z",
  "updated_at": "2026-06-25T10:00:00Z"
}
```

**Ошибки:**

| Статус | Описание |
|--------|----------|
| 404 | Профиль пользователя не найден |

---

### PATCH /api/v1/public/users/me

Обновление профиля текущего пользователя (partial update). Обновляются только переданные поля.

**Тело запроса:**

```json
{
  "first_name": "Пётр",
  "bio": "Новый разработчик"
}
```

| Поле | Тип | Валидация |
|------|-----|-----------|
| first_name | str \| null | Макс. 100 символов |
| last_name | str \| null | Макс. 100 символов |
| avatar_url | str \| null | Макс. 500 символов |
| bio | str \| null | Без ограничения |

Все поля опциональны. Неуказанные поля не изменяются.

**Ответ 200:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "auth_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "first_name": "Пётр",
  "last_name": "Иванов",
  "avatar_url": null,
  "bio": "Новый разработчик",
  "created_at": "2026-06-25T10:00:00Z",
  "updated_at": "2026-06-25T10:30:00Z"
}
```

**Ошибки:**

| Статус | Описание |
|--------|----------|
| 404 | Профиль пользователя не найден |

---

### DELETE /api/v1/public/users/me

Удаление профиля текущего пользователя.

**Ответ 204:** Пустое тело.

**Ошибки:**

| Статус | Описание |
|--------|----------|
| 404 | Профиль пользователя не найден |

---

## Типичный сценарий

```
1. POST /api/v1/public/auth/register     → получаем JWT-токен
2. POST /api/v1/public/users/            → создаём профиль (с токеном из п.1)
3. GET  /api/v1/public/users/me          → получаем профиль
4. PATCH /api/v1/public/users/me         → обновляем профиль
5. DELETE /api/v1/public/users/me        → удаляем профиль
```

---

## Telegram Clients

> Все эндпоинты требуют авторизацию: `Authorization: Bearer <token>`

### POST /telegram-clients/api/v1/public/auth/phone

Шаг 1 авторизации: отправка номера телефона для получения SMS-кода.

**Тело запроса:**

```json
{
  "phone": "+79001234567"
}
```

| Поле | Тип | Валидация |
|------|-----|-----------|
| phone | str | Обязательное, макс. 20 символов |

**Ответ 200:**

```json
{
  "account_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "code_sent"
}
```

---

### POST /telegram-clients/api/v1/public/auth/code

Шаг 2 авторизации: ввод SMS-кода.

**Тело запроса:**

```json
{
  "account_id": "550e8400-e29b-41d4-a716-446655440000",
  "code": "12345"
}
```

| Поле | Тип | Валидация |
|------|-----|-----------|
| account_id | UUID | Обязательное |
| code | str | Обязательное, макс. 10 символов |

**Ответ 200 (подключён):**

```json
{
  "account_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "connected"
}
```

**Ответ 200 (требуется 2FA):**

```json
{
  "account_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "2fa_required"
}
```

**Ошибки:**

| Статус | Описание |
|--------|----------|
| 404 | Аккаунт не найден или не принадлежит текущему пользователю |

---

### POST /telegram-clients/api/v1/public/auth/password

Шаг 3 авторизации: ввод пароля облачного шифрования (2FA).

**Тело запроса:**

```json
{
  "account_id": "550e8400-e29b-41d4-a716-446655440000",
  "password": "my_cloud_password"
}
```

| Поле | Тип | Валидация |
|------|-----|-----------|
| account_id | UUID | Обязательное |
| password | str | Обязательное |

**Ответ 200:**

```json
{
  "account_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "connected"
}
```

**Ошибки:**

| Статус | Описание |
|--------|----------|
| 404 | Аккаунт не найден или не принадлежит текущему пользователю |

---

### GET /telegram-clients/

Список всех Telegram-аккаунтов текущего пользователя.

**Ответ 200:**

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "auth_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "phone": "+79001234567",
    "is_connected": true,
    "first_name": "Иван",
    "last_name": "Иванов",
    "username": "ivan",
    "telegram_id": 123456789,
    "created_at": "2026-06-25T10:00:00Z",
    "updated_at": "2026-06-25T10:00:00Z"
  }
]
```

---

### DELETE /telegram-clients/{account_id}

Удалить Telegram-аккаунт. Отключает клиент, удаляет session-файл и запись из БД.

**Ответ 204:** Пустое тело.

**Ошибки:**

| Статус | Описание |
|--------|----------|
| 404 | Аккаунт не найден или не принадлежит текущему пользователю |

---

### GET /telegram-clients/{account_id}/chats

Получить все чаты указанного Telegram-аккаунта (on-demand из Telegram API).

**Ответ 200:**

```json
[
  {
    "id": -1001234567890,
    "name": "Мой чат",
    "chat_type": "private",
    "username": "someuser"
  }
]
```

**Ошибки:**

| Статус | Описание |
|--------|----------|
| 404 | Аккаунт не найден |
| 409 | Аккаунт не подключён |

---

### GET /telegram-clients/{account_id}/chats/{chat_id}/messages

Получить сообщения указанного чата (on-demand из Telegram API).

**Параметры запроса:**

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| limit | int | 50 | Количество сообщений (1–200) |

**Ответ 200:**

```json
[
  {
    "id": 42,
    "chat_id": -1001234567890,
    "sender_id": 123456789,
    "text": "Привет!",
    "media": [
      {"type": "photo", "id": "AQADBAAT..."}
    ],
    "date": "2026-06-25T10:00:00Z"
  }
]
```

**Ошибки:**

| Статус | Описание |
|--------|----------|
| 404 | Аккаунт не найден |
| 409 | Аккаунт не подключён |

---

## Типичный сценарий (Telegram)

```
1. POST /telegram-clients/api/v1/public/auth/phone   → отправляем номер
2. POST /telegram-clients/api/v1/public/auth/code    → вводим SMS-код
3. POST /telegram-clients/api/v1/public/auth/password → вводим 2FA (если нужно)
4. GET  /telegram-clients/             → список аккаунтов
5. GET  /telegram-clients/{id}/chats   → список чатов
6. GET  /telegram-clients/{id}/chats/{chat_id}/messages → сообщения
7. DELETE /telegram-clients/{id}       → удалить аккаунт
```

---

## Notifications

> Эндпоинты шаблонов и истории требуют авторизацию: `Authorization: Bearer <token>`
> История доступна только администраторам (role=admin)

### POST /api/v1/public/notifications/templates/

Создать шаблон уведомления.

**Тело запроса:**

```json
{
  "name": "welcome",
  "channel": "email",
  "subject_template": "Добро пожаловать, {{ first_name }}!",
  "body_template": "<h1>Привет, {{ first_name }}!</h1>",
  "is_active": true
}
```

| Поле | Тип | Валидация |
|------|-----|-----------|
| name | str | Обязательное, макс. 100 символов, уникальное |
| channel | str | Макс. 20 символов, default "email" |
| subject_template | str \| null | Jinja2-шаблон темы |
| body_template | str | Обязательное, Jinja2-шаблон тела |
| is_active | bool | Default true |

**Ответ 201:** TemplateRead

---

### GET /api/v1/public/notifications/templates/

Список шаблонов.

**Параметры запроса:**

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| skip | int | 0 | Смещение |
| limit | int | 100 | Лимит (1–500) |

**Ответ 200:** list[TemplateRead]

---

### GET /api/v1/public/notifications/templates/{id}

Получить шаблон по ID.

**Ответ 200:** TemplateRead

**Ошибки:**

| Статус | Описание |
|--------|----------|
| 404 | Шаблон не найден |

---

### PATCH /api/v1/public/notifications/templates/{id}

Обновить шаблон (partial update).

**Ответ 200:** TemplateRead

---

### DELETE /api/v1/public/notifications/templates/{id}

Удалить шаблон.

**Ответ 204:** Пустое тело.

---

### GET /api/v1/public/notifications/history/

История уведомлений. **Только для администраторов.**

**Параметры запроса:**

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| skip | int | 0 | Смещение |
| limit | int | 50 | Лимит (1–200) |

**Ответ 200:** list[NotificationLogRead]

---

## Internal

> Роуты без авторизации. Доступ ограничен network-level (Docker/k8s).

### GET /internal/api/v1/public/users/

Получить пользователей с фильтрацией (для межмодульного взаимодействия).

**Параметры запроса:**

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| filters | list[str] | [] | Фильтры формата `field+operator+value` |
| skip | int | 0 | Смещение |
| limit | int | 100 | Лимит (1–500) |

**Операторы фильтров:**

| Оператор | Описание | Пример |
|----------|----------|--------|
| eq | Равно | `auth_id+eq+uuid` |
| ne | Не равно | `status+ne+deleted` |
| gt | Больше | `age+gt+18` |
| ge | Больше или равно | `age+ge+18` |
| lt | Меньше | `age+lt+65` |
| le | Меньше или равно | `age+le+65` |
| like | LIKE | `name+like+%test%` |
| ilike | ILIKE | `name+ilike+%ivan%` |
| in | В списке | `status+in+active,pending` |

**Примеры:**

```
GET /internal/api/v1/public/users/?filters=auth_id+eq+550e8400-...
GET /internal/api/v1/public/users/?filters=email+eq+test@test.com
GET /internal/api/v1/public/users/?filters=auth_id+eq+...&filters=email+eq+...
```

**Ответ 200:** list[UserRead]

---

## Media

> Публичные эндпоинты `/api/v1/public/media/` требуют авторизацию для upload/delete.
> Внутренние эндпоинты `/internal/api/v1/public/media/` — без авторизации (network-level доступ).

### POST /api/v1/public/media/

Загрузить файл. Требуется авторизация.

**Формат:** `multipart/form-data`

**Параметры:**

| Параметр | Тип | Валидация | Описание |
|----------|-----|-----------|----------|
| file | UploadFile | Обязательное, макс. 5MB | Файл для загрузки |
| is_public | bool | Default false | Публичный доступ (true/false) |

**Ответ 201:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "document.pdf",
  "content_type": "application/pdf",
  "size_bytes": 102400,
  "storage_key": "ab/cd/550e8400-e29b-41d4-a716-446655440000.pdf",
  "is_public": true,
  "url": "/api/v1/public/media/550e8400-e29b-41d4-a716-446655440000"
}
```

**Ошибки:**

| Статус | Описание |
|--------|----------|
| 400 | Файл не предоставлен или превышает лимит (5MB) |
| 401 | Требуется авторизация |

---

### GET /api/v1/public/media/{file_id}

Получить метаданные файла.

**Ответ 200:** FileRead

**Ошибки:**

| Статус | Описание |
|--------|----------|
| 404 | Файл не найден или не публичный |

---

### GET /api/v1/public/media/{file_id}/download

Скачать файл (потоком). Доступен только для файлов с `is_public=true`.

**Ответ 200:** Файл (потоковая передача)

- `Content-Type`: оригинальный content_type файла
- `Content-Disposition`: attachment; filename="..."

**Ошибки:**

| Статус | Описание |
|--------|----------|
| 403 | Файл не публичный |
| 404 | Файл не найден |

---

### DELETE /api/v1/public/media/{file_id}

Удалить файл. Требуется авторизация.

**Ответ 204:** Пустое тело.

**Ошибки:**

| Статус | Описание |
|--------|----------|
| 401 | Требуется авторизация |
| 404 | Файл не найден |

---

## Internal Media

> Эндпоинты без авторизации. Доступ ограничен network-level.

### POST /internal/api/v1/public/media/

Загрузить файл (без проверки авторизации и is_public).

**Формат:** `multipart/form-data`

**Параметры:**

| Параметр | Тип | Валидация | Описание |
|----------|-----|-----------|----------|
| file | UploadFile | Обязательное, макс. 5MB | Файл для загрузки |
| is_public | bool | Default false | Публичный доступ |

**Ответ 201:** FileUploadResponse

---

### GET /internal/api/v1/public/media/{file_id}

Получить метаданные файла (без проверки is_public).

**Ответ 200:** FileRead

---

### GET /internal/api/v1/public/media/{file_id}/download

Скачать файл (потоком, без проверки is_public).

**Ответ 200:** Файл (потоковая передача)

- `Content-Type`: оригинальный content_type файла
- `Content-Disposition`: attachment; filename="..."

---

### DELETE /internal/api/v1/public/media/{file_id}

Удалить файл (без проверки авторизации).

**Ответ 204:** Пустое тело.

---

## HTTP-клиенты для межмодульного взаимодействия

Для синхронного межмодульного взаимодействия используются HTTP-клиенты, вынесенные в `src/core/clients/`. Это устраняет дублирование кода и обеспечивает единую точку расширения.

### Расположение

```
src/core/clients/
├── __init__.py
├── base.py              # BaseHTTPClient — базовый класс
├── users_client.py      # UsersHTTPClient
└── media_client.py      # MediaHTTPClient
```

### Базовый класс: `BaseHTTPClient`

**Расположение:** `src/core/clients/base.py`

Базовый класс для всех HTTP-клиентов. Обеспечивает:
- Автоматическое использование `INTERNAL_API_BASE_URL` из настроек
- Таймаут по умолчанию (10 секунд)
- Обработку ошибок с логированием
- Базовые методы: `get()`, `post()`, `delete()`

**Инициализация:**
```python
client = BaseHTTPClient(base_url="http://localhost:8000/internal", timeout=30.0)
```

**Методы:**
- `get(path, **kwargs) -> httpx.Response | None`
- `post(path, **kwargs) -> httpx.Response | None`
- `delete(path, **kwargs) -> httpx.Response | None`

**Пример использования:**
```python
from src.core.clients.base import BaseHTTPClient

client = BaseHTTPClient()
response = await client.get("/api/v1/public/users/", params={"filters": "auth_id+eq+uuid"})
```

---

### `UsersHTTPClient`

**Расположение:** `src/core/clients/users_client.py`

Клиент для взаимодействия с модулем `users`.

**Методы:**

#### `resolve_user_by_auth_id(auth_id: UUID) -> str | None`

Резолвит email пользователя по `auth_id`.

**Параметры:**
- `auth_id` — UUID учётной записи пользователя

**Возвращает:**
- Email пользователя (если найден)
- `None` (если не найден или ошибка)

**Внутренний запрос:**
```
GET /internal/api/v1/public/users/?filters=auth_id+eq+{auth_id}
```

**Пример:**
```python
from src.core.clients import UsersHTTPClient
import uuid

users_client = UsersHTTPClient()
auth_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
email = await users_client.resolve_user_by_auth_id(auth_id)

if email:
    print(f"Email пользователя: {email}")
else:
    print("Пользователь не найден")
```

**Использование в модуле `notifications`:**
```python
from src.core.clients import UsersHTTPClient

class NotificationService:
    def __init__(self):
        self.users_client = UsersHTTPClient()
    
    async def send_notification(self, auth_id: uuid.UUID, template_name: str, **kwargs):
        # Резолвим email для отправки уведомления
        email = await self.users_client.resolve_user_by_auth_id(auth_id)
        if email:
            await self.send_email(email, template_name, **kwargs)
```

---

### `MediaHTTPClient`

**Расположение:** `src/core/clients/media_client.py`

Клиент для взаимодействия с модулем `media`.

**Методы:**

#### `upload_media_to_storage(file_bytes: bytes, filename: str, content_type: str, is_public: bool = False) -> str | None`

Загружает файл в хранилище.

**Параметры:**
- `file_bytes` — бинарные данные файла
- `filename` — оригинальное имя файла
- `content_type` — MIME-тип (например, `image/png`)
- `is_public` — публичный доступ (default: `False`)

**Возвращает:**
- `file_id` (UUID) при успехе
- `None` при ошибке

**Внутренний запрос:**
```
POST /internal/api/v1/public/media/
Content-Type: multipart/form-data
```

**Пример:**
```python
from src.core.clients import MediaHTTPClient

media_client = MediaHTTPClient()

with open("document.pdf", "rb") as f:
    file_bytes = f.read()

file_id = await media_client.upload_media_to_storage(
    file_bytes=file_bytes,
    filename="document.pdf",
    content_type="application/pdf",
    is_public=True,
)

if file_id:
    print(f"Файл загружен: {file_id}")
```

#### `get_media_file(file_id: str) -> bytes | None`

Скачивает файл по ID.

**Параметры:**
- `file_id` — UUID файла

**Возвращает:**
- Бинарные данные файла при успехе
- `None` при ошибке

**Внутренний запрос:**
```
GET /internal/api/v1/public/media/{file_id}/download
```

**Пример:**
```python
file_data = await media_client.get_media_file("550e8400-e29b-41d4-a716-446655440000")
if file_data:
    with open("downloaded.pdf", "wb") as f:
        f.write(file_data)
```

#### `delete_media_file(file_id: str) -> bool`

Удаляет файл по ID.

**Параметры:**
- `file_id` — UUID файла

**Возвращает:**
- `True` при успехе
- `False` при ошибке

**Внутренний запрос:**
```
DELETE /internal/api/v1/public/media/{file_id}
```

**Пример:**
```python
success = await media_client.delete_media_file("550e8400-e29b-41d4-a716-446655440000")
if success:
    print("Файл удалён")
```

---

## Настройки

HTTP-клиенты используют переменную окружения `INTERNAL_API_BASE_URL`:

```env
INTERNAL_API_BASE_URL=http://localhost:8000/internal
```

Для развёртывания в Kubernetes или Docker Compose измените на внутренний DNS:

```env
INTERNAL_API_BASE_URL=http://ms_starter_app:8000/internal
```

---

## См. также

- [Архитектура](architecture.md) — раздел "Общие HTTP-клиенты"
- [Внутренние роуты](api.md#internal) — API для межмодульного взаимодействия
- [Фильтрация](filters.md) — использование фильтров в запросах
