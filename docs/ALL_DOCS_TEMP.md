# Объединённая документация проекта ms_starter

> **Временный файл** — не для коммита в git. Содержит всю документацию из папки docs/.

---

## Оглавление

1. [Архитектура](#архитектура)
2. [API документация](#api-документация)
3. [Шина сообщений](#шина-сообщений)
4. [Модели базы данных](#модели-базы-данных)
5. [Запуск и развёртывание](#запуск-и-развёртывание)
6. [Универсальная фильтрация запросов](#универсальная-фильтрация-запросов)
7. [Правила изоляции модулей](#правила-изоли-модулей)
8. [Как добавить новый модуль](#как-добавить-новый-модуль)

---

# Архитектура

## Обзор

Сервис построен по принципу **Modular Monolith** — приложение состоит из изолированных модулей, работающих в одном процессе. Каждый модуль спроектирован так, чтобы в будущем его можно было вынести в отдельный микросервис **без переписывания бизнес-логики**.

## Принципы

| Принцип | Описание |
|---------|----------|
| **Изоляция модулей** | Модули не импортируют друг друга напрямую |
| **Связь через шину** | Взаимодействие между модулями — только через события (MessageBus) |
| **Интерфейсы (Protocol)** | Зависимости между модулями — через абстракции, не реализации |
| **Нет ForeignKey между модулями** | Каждая таблица принадлежит одному модулю, связи — по UUID |
| **DI-контейнер** | FastAPI Depends для внедрения зависимостей |
| **Единый реестр топиков** | Все топики шины определены в `BusTopics` — нет хардкода строк |

## Стек технологий

| Компонент | Технология |
|-----------|------------|
| Язык | Python 3.11+ |
| Фреймворк | FastAPI |
| БД | PostgreSQL |
| ORM | SQLAlchemy 2.0 (async) |
| Миграции | Alembic |
| Валидация | Pydantic v2 |
| Настройки | pydantic-settings |
| Драйвер БД | asyncpg |
| Хэширование | bcrypt |
| JWT | PyJWT |
| Шина сообщений | aiokafka / in-memory |
| Telegram API | Telethon |

## Структура проекта

```
src/
├── base/                        # Базовые абстракции
│   ├── model.py                 # Base, BaseModel — абстрактная модель с id, created_at, updated_at
│   ├── repository.py            # BaseRepository — дженерик CRUD
│   └── service.py               # BaseService — прокси над репозиторием
│
├── core/                        # Ядро приложения
│   ├── config.py                # Settings — настройки из .env
│   ├── database.py              # engine, async_sessionmaker, get_session
│   ├── security.py              # hash_password, verify_password, JWT
│   ├── exceptions.py            # AppException, NotFoundError, ConflictError, UnauthorizedError
│   ├── dependencies.py          # FastAPI Depends (get_db_session, get_current_user, фабрики сервисов)
│   └── bus_topics.py            # BusTopics — реестр всех топиков шины
│
├── bus/                         # Шина сообщений
│   ├── interface.py             # MessageBus (Protocol) — интерфейс шины
│   ├── schemes.py               # BaseEvent — базовый класс событий
│   ├── in_memory/               # In-memory реализация (для монолита)
│   │   ├── producer.py          # InMemoryProducer
│   │   └── consumer.py          # InMemoryConsumer
│   └── kafka/                   # Kafka реализация (для микросервисов)
│       ├── producer.py          # KafkaProducerBus
│       └── consumer.py          # KafkaConsumerRouter
│
├── modules/                     # Бизнес-модули
│   ├── auth/                    # Модуль авторизации
│   │   ├── models.py            # Auth (identifier, hashed_password, role)
│   │   ├── schemas/public/auth.py       # TokenResponse
│   │   ├── schemas/internal/auth.py     # AuthCreate, AuthRead, AuthUpdate
│   │   ├── schemas/events.py    # UserRegistered, UserLoggedIn
│   │   ├── repository.py        # AuthRepository (+ get_by_identifier)
│   │   ├── service.py           # AuthService (register, login)
│   │   └── router.py            # POST /auth/register, POST /auth/login
│   │
│   └── users/                   # Модуль пользователей
│       ├── models.py            # User (auth_id, first_name, last_name, avatar_url, bio), Telegram
│       ├── schemas/public/user.py       # UserCreate, UserRead, UserUpdate
│       ├── schemas/internal/user.py     # UserCreate, UserRead, UserUpdate
│       ├── schemas/events.py    # ProfileCreated, ProfileUpdated, ProfileDeleted
│       ├── repository.py        # UserRepository (+ get_by_auth_id), TelegramRepository
│       ├── service.py           # UserService (create, get, update, delete)
│       ├── handlers.py          # Обработчики событий из шины
│       └── router.py            # POST /users/, GET /users/me, PATCH /users/me, DELETE /users/me
│
│   └── telegram_clients/        # Модуль Telegram-клиентов
│       ├── models.py            # TelegramAccount (auth_id, phone, session_file, is_connected, ...)
│       ├── schemas/api.py       # PhoneRequest, CodeRequest, PasswordRequest, AccountRead, ChatRead, MessageRead
│       ├── schemas/events.py    # TgMessageReceived, TgMessageSend, TgAccountConnected, TgAccountDisconnected
│       ├── repository.py        # TelegramAccountRepository (+ get_by_auth_id, get_connected_accounts)
│       ├── client_manager.py    # TelegramClientManager — singleton управления Telethon-клиентами
│       ├── service.py           # TelegramClientService (auth, CRUD, chats, messages)
│       ├── handlers.py          # Подписка на tg.message.send
│       └── router.py            # POST /auth/phone, /auth/code, /auth/password, GET /, DELETE /{id}, chats, messages
│
│   └── notifications/           # Модуль нотификаций
│       ├── models.py            # NotificationTemplate, NotificationLog
│       ├── schemas/api.py       # TemplateCreate, TemplateRead, TemplateUpdate, NotificationLogRead
│       ├── schemas/events.py    # NotificationSend
│       ├── repository.py        # NotificationTemplateRepository, NotificationLogRepository
│       ├── providers/           # Абстракция провайдеров (Protocol + SMTP)
│       │   ├── base.py          # NotificationProvider (Protocol)
│       │   └── smtp.py          # SmtpProvider (aiosmtplib)
│       ├── template_engine.py   # Jinja2 рендеринг (БД → файлы)
│       ├── service.py           # NotificationService (шаблоны, отправка, история)
│       ├── handlers.py          # Подписка на notification.send
│       └── router.py            # CRUD шаблонов, история (admin)
│
│   └── media/                   # Модуль медиа-файлов
│       ├── models.py            # StoredFile (id, filename, content_type, size_bytes, storage_key, is_public)
│       ├── schemas/api.py       # FileRead, FileUploadResponse
│       ├── schemas/events.py    # MediaUploaded, MediaDeleted
│       ├── repository.py        # StoredFileRepository
│       ├── storage/             # Абстракция хранилищ (Protocol + LocalStorage)
│       │   ├── base.py          # StorageProvider (Protocol: put, get, delete, generate_url)
│       │   └── local.py         # LocalStorage (2-level sharding: ab/cd/uuid.ext)
│       ├── service.py           # MediaService (upload, get, download, delete)
│       ├── handlers.py          # register_handlers placeholder
│       └── routers/             # Разделение публичных и внутренних роутов
│           ├── __init__.py      # Экспорт public_router, internal_router
│           ├── public.py        # /media/ (JWT для upload/delete, is_public для GET)
│           └── internal.py      # /internal/media/ (без JWT, без is_public проверок)
│
└── main.py                      # Точка входа: инициализация шины, ClientManager, LocalStorage, lifespan, FastAPI app
```

## Слои внутри модуля

Каждый модуль следует трёхслойной архитектуре:

```
Router (HTTP) → Service (бизнес-логика) → Repository (БД)
     │                  │
     │                  └──→ MessageBus (события)
     │
     └──→ Depends (DI-контейнер)
```

- **Router** — принимает HTTP-запросы, валидирует через Pydantic, вызывает сервис
- **Service** — содержит бизнес-логику, публикует события, не знает про HTTP
- **Repository** — работает с SQLAlchemy, не знает про бизнес-логику

## Особенность: ClientManager

Модуль `telegram_clients` содержит уникальный компонент — `TelegramClientManager`. Это singleton, который не вписывается в стандартную трёхслойную архитектуру, так как Telethon требует держать подключение открытым для получения входящих сообщений.

```
TelegramClientManager (singleton)
├── clients: dict[account_id, TelegramClient]
├── on_new_message → publish(TG_MESSAGE_RECEIVED)
├── send_message(account_id, chat_id, text)
├── connect_account / disconnect_account
└── get_chats / get_messages / get_me
```

**Жизненный цикл:**
- **Startup** — загружает все `is_connected=True` аккаунты из БД и подключает их
- **Runtime** — держит подключения открытыми, обрабатывает входящие сообщения
- **Shutdown** — отключает все клиенты

Сервис делегирует работу с Telethon клиент-менеджеру, а персистентность — репозиторию.

## Роли пользователей

Модель `Auth` содержит поле `role` (`user` / `admin`). Роль записывается в JWT и проверяется через зависимости:

| Зависимость | Описание |
|-------------|----------|
| `get_current_user` | Любой авторизованный пользователь |
| `get_current_admin` | Только администратор (role=admin) |

Роль по умолчанию — `user`. Администраторы создаются вручную через БД или специальный эндпоинт.

## Фильтрация (base/filters.py)

Универсальная фильтрация для репозиториев и внутренних роутов. Формат: `field+operator+value`.

```python
# Пример: GET /internal/users/?filters=auth_id+eq+550e8400-...&filters=email+eq+test@test.com
filters = parse_filters(["auth_id+eq+550e8400-...", "email+eq+test@test.com"])
stmt = apply_filters(stmt, MyModel, filters)
```

Операторы: `eq`, `ne`, `gt`, `ge`, `lt`, `le`, `like`, `ilike`, `in`.

## Внутренние роуты (/internal/)

Роуты с префиксом `/internal/` — для межмодульного взаимодействия. Без JWT-авторизации, доступ ограничен network-level (Docker network, k8s NetworkPolicy).

## Межмодульное взаимодействие

Модули **не импортируют друг друга напрямую**. Для взаимодействия используются:

1. **Шина событий (MessageBus)** — для асинхронной связи (fire-and-forget)
2. **HTTP-запросы к `/internal/`** — для синхронных запросов между модулями

**Пример:** Если модулю `notifications` нужно получить файл из модуля `media`:

```python
# НЕПРАВИЛЬНО:
from src.modules.media.service import MediaService  # прямой импорт запрещён

# ПРАВИЛЬНО:
async with httpx.AsyncClient() as client:
    response = await client.get(f"http://localhost:8000/internal/media/{file_id}")
    file_data = response.json()
```

**Пример для notifications модуля:** Резолв email по auth_id через internal API users:

```python
from src.modules.notifications.http_client import resolve_user_by_auth_id

# Внутри сервиса нотификаций
email = await resolve_user_by_auth_id(auth_id)
if email:
    await send_email(email, subject, body)
```

URL внутреннего API вынесен в настройки: `settings.INTERNAL_API_BASE_URL = "http://localhost:8000/internal"`.

## Общие HTTP-клиенты (src/core/clients/)

Для устранения дублирования кода общие HTTP-клиенты вынесены в модуль `src/core/clients/`:

| Клиент | Методы | Описание |
|--------|--------|----------|
| `UsersHTTPClient` | `resolve_user_by_auth_id(auth_id)` | Резолв email по auth_id |
| `MediaHTTPClient` | `upload_media_to_storage(...)`, `get_media_file(file_id)`, `delete_media_file(file_id)` | Работа с media модулем |

**Пример использования:**

```python
# В любом модуле:
from src.core.clients import UsersHTTPClient, MediaHTTPClient

users_client = UsersHTTPClient()
email = await users_client.resolve_user_by_auth_id(auth_id)

media_client = MediaHTTPClient()
file_id = await media_client.upload_media_to_storage(...)
```

**Преимущества:**
- Устранение дублирования кода
- Единая точка расширения
- Упрощение тестирования

Модуль `media` спроектирован как независимый сервис — файлы не имеют владельца (`auth_id`), доступ контролируется через `is_public` (публичный доступ) или network-level (внутренний API).

## Шина сообщений

### Провайдеры (`src/bus/providers.py`)

Отдельный модуль для инициализации шины — **без циклических зависимостей**:

```python
# src/bus/providers.py
from src.bus.interface import MessageBus
from src.core.config import settings


def get_message_bus() -> MessageBus:
    """Создаёт экземпляр продюсера на основе конфигурации."""
    if settings.MESSAGE_BUS == "kafka":
        from src.bus.kafka.producer import KafkaProducerBus
        return KafkaProducerBus()
    from src.bus.in_memory.producer import InMemoryProducer
    return InMemoryProducer()
```

**Зачем?**
- `main.py` и `dependencies.py` используют один провайдер — нет дублирования
- При переключении с in-memory на Kafka — меняется только `providers.py`
- Циклические зависимости устранены: `main.py` → `providers.py` → `dependencies.py`

## DI-зависимости

### Модульные зависимости (`src/modules/*/dependencies.py`)

Каждый модуль регистрирует свои зависимости **внутри себя**:

```
src/modules/
├── auth/dependencies.py          # get_auth_service()
├── users/dependencies.py         # get_user_service()
├── telegram_clients/dependencies.py  # get_telegram_client_service()
├── notifications/dependencies.py # get_notification_service()
├── media/dependencies.py         # get_media_service()
```

**Ядро (`src/core/dependencies.py`)** содержит только **общие** зависимости:
- `get_db_session()` — сессия БД
- `get_current_user()` / `get_current_admin()` — JWT-авторизация
- `get_users_client()` / `get_media_client()` — клиенты для межмодульного взаимодействия

---

# API документация

## Общая информация

- Базовый URL: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- Формат тела запроса/ответа: `application/json`
- Авторизация: `Bearer <JWT-токен>` в заголовке `Authorization`

---

## Auth

### POST /public/auth/register

Регистрация нового пользователя. Создаёт учётную запись авторизации и возвращает JWT-токен.

Поддерживает регистрацию по **email**, **телефону** ИЛИ **telegram username**.

Профиль пользователя создаётся **отдельным запросом** `POST /public/users/`.

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

### POST /public/auth/login

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

### POST /public/users/

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

### GET /public/users/me

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

### PATCH /public/users/me

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

### DELETE /public/users/me

Удаление профиля текущего пользователя.

**Ответ 204:** Пустое тело.

**Ошибки:**

| Статус | Описание |
|--------|----------|
| 404 | Профиль пользователя не найден |

---

## Типичный сценарий

```
1. POST /public/auth/register     → получаем JWT-токен
2. POST /public/users/            → создаём профиль (с токеном из п.1)
3. GET  /public/users/me          → получаем профиль
4. PATCH /public/users/me         → обновляем профиль
5. DELETE /public/users/me        → удаляем профиль
```

---

## Telegram Clients

> Все эндпоинты требуют авторизацию: `Authorization: Bearer <token>`

### POST /telegram-clients/public/auth/phone

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

### POST /telegram-clients/public/auth/code

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

### POST /telegram-clients/public/auth/password

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
1. POST /telegram-clients/public/auth/phone   → отправляем номер
2. POST /telegram-clients/public/auth/code    → вводим SMS-код
3. POST /telegram-clients/public/auth/password → вводим 2FA (если нужно)
4. GET  /telegram-clients/             → список аккаунтов
5. GET  /telegram-clients/{id}/chats   → список чатов
6. GET  /telegram-clients/{id}/chats/{chat_id}/messages → сообщения
7. DELETE /telegram-clients/{id}       → удалить аккаунт
```

---

## Notifications

> Эндпоинты шаблонов и истории требуют авторизацию: `Authorization: Bearer <token>`
> История доступна только администраторам (role=admin)

### POST /public/notifications/templates/

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

### GET /public/notifications/templates/

Список шаблонов.

**Параметры запроса:**

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| skip | int | 0 | Смещение |
| limit | int | 100 | Лимит (1–500) |

**Ответ 200:** list[TemplateRead]

---

### GET /public/notifications/templates/{id}

Получить шаблон по ID.

**Ответ 200:** TemplateRead

**Ошибки:**

| Статус | Описание |
|--------|----------|
| 404 | Шаблон не найден |

---

### PATCH /public/notifications/templates/{id}

Обновить шаблон (partial update).

**Ответ 200:** TemplateRead

---

### DELETE /public/notifications/templates/{id}

Удалить шаблон.

**Ответ 204:** Пустое тело.

---

### GET /public/notifications/history/

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

### GET /internal/public/users/

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
GET /internal/public/users/?filters=auth_id+eq+550e8400-...
GET /internal/public/users/?filters=email+eq+test@test.com
GET /internal/public/users/?filters=auth_id+eq+...&filters=email+eq+...
```

**Ответ 200:** list[UserRead]

---

## Media

> Публичные эндпоинты `/public/media/` требуют авторизацию для upload/delete.
> Внутренние эндпоинты `/internal/public/media/` — без авторизации (network-level доступ).

### POST /public/media/

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
  "url": "/public/media/550e8400-e29b-41d4-a716-446655440000"
}
```

**Ошибки:**

| Статус | Описание |
|--------|----------|
| 400 | Файл не предоставлен или превышает лимит (5MB) |
| 401 | Требуется авторизация |

---

### GET /public/media/{file_id}

Получить метаданные файла.

**Ответ 200:** FileRead

**Ошибки:**

| Статус | Описание |
|--------|----------|
| 404 | Файл не найден или не публичный |

---

### GET /public/media/{file_id}/download

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

### DELETE /public/media/{file_id}

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

### POST /internal/public/media/

Загрузить файл (без проверки авторизации и is_public).

**Формат:** `multipart/form-data`

**Параметры:**

| Параметр | Тип | Валидация | Описание |
|----------|-----|-----------|----------|
| file | UploadFile | Обязательное, макс. 5MB | Файл для загрузки |
| is_public | bool | Default false | Публичный доступ |

**Ответ 201:** FileUploadResponse

---

### GET /internal/public/media/{file_id}

Получить метаданные файла (без проверки is_public).

**Ответ 200:** FileRead

---

### GET /internal/public/media/{file_id}/download

Скачать файл (потоком, без проверки is_public).

**Ответ 200:** Файл (потоковая передача)

- `Content-Type`: оригинальный content_type файла
- `Content-Disposition`: attachment; filename="..."

---

### DELETE /internal/public/media/{file_id}

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
response = await client.get("/public/users/", params={"filters": "auth_id+eq+uuid"})
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
GET /internal/public/users/?filters=auth_id+eq+{auth_id}
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
POST /internal/public/media/
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
GET /internal/public/media/{file_id}/download
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
DELETE /internal/public/media/{file_id}
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

---

# Шина сообщений

## Обзор

Шина сообщений — механизм взаимодействия между модулями без прямых импортов. Модули публикуют события, другие модули подписываются на них.

### Интерфейс

Все реализации шины следуют протоколу `MessageBus` (`src/bus/interface.py`):

```python
class MessageBus(Protocol):
    def publish(self, topic: str, message: dict) -> None: ...
    def subscribe(self, topic: str) -> Callable: ...
    def get_subscribers(self) -> dict[str, list[Callable]]: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
```

### Реализации

| Реализация | Когда использовать | Описание |
|------------|-------------------|----------|
| `InMemoryProducer` + `InMemoryConsumer` | Монолит (по умолчанию) | Обработчики вызываются в том же процессе |
| `KafkaProducerBus` + `KafkaConsumerRouter` | Микросервисы | Сообщения через Kafka-брокер |

Переключение — одна переменная в `.env`:

```env
MESSAGE_BUS=in_memory    # или kafka
```

---

## Реестр топиков

Все топики определены в `src/core/bus_topics.py` — **единственная точка истины**. Хардкод строк в коде запрещён.

| Константа | Топик | Модуль-источник | Описание |
|-----------|-------|-----------------|----------|
| `BusTopics.USER_REGISTERED` | `user.registered` | auth | Пользователь зарегистрирован |
| `BusTopics.USER_LOGGED_IN` | `user.logged_in` | auth | Пользователь авторизовался |
| `BusTopics.PROFILE_CREATED` | `profile.created` | users | Профиль создан |
| `BusTopics.PROFILE_UPDATED` | `profile.updated` | users | Профиль обновлён |
| `BusTopics.PROFILE_DELETED` | `profile.deleted` | users | Профиль удалён |
| `BusTopics.TG_MESSAGE_RECEIVED` | `tg.message.received` | telegram_clients | Входящее сообщение из Telegram |
| `BusTopics.TG_MESSAGE_SEND` | `tg.message.send` | telegram_clients | Отправить сообщение через аккаунт |
| `BusTopics.TG_ACCOUNT_CONNECTED` | `tg.account.connected` | telegram_clients | Аккаунт подключён |
| `BusTopics.TG_ACCOUNT_DISCONNECTED` | `tg.account.disconnected` | telegram_clients | Аккаунт отключён |
| `BusTopics.NOTIFICATION_SEND` | `notification.send` | notifications | Отправить уведомление |
| `BusTopics.MEDIA_UPLOADED` | `media.uploaded` | media | Файл загружен |
| `BusTopics.MEDIA_DELETED` | `media.deleted` | media | Файл удалён |

---

## События

Все события наследуются от `BaseEvent` (`src/bus/schemes.py`), который предоставляет:

- `timestamp` — автоматическая дата/время в UTC
- `to_bus_dict()` — сериализация через `model_dump(mode="json")` с добавлением `event_name`

### UserRegistered

Топик: `user.registered`
Источник: `AuthService.register()`

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"user.registered"` |
| auth_id | UUID | ID учётной записи |
| email | str | Email пользователя |
| timestamp | datetime | Время события |

### UserLoggedIn

Топик: `user.logged_in`
Источник: `AuthService.login()`

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"user.logged_in"` |
| auth_id | UUID | ID учётной записи |
| email | str | Email пользователя |
| timestamp | datetime | Время события |

### UserDeleted

Топик: `user.deleted`
Источник: `AuthService.delete_account()`

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"user.deleted"` |
| auth_id | UUID | ID удалённой учётной записи |

### ProfileCreated

Топик: `profile.created`
Источник: `UserService.create_user_profile()`

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"profile.created"` |
| auth_id | UUID | ID учётной записи |
| profile_id | UUID | ID профиля |
| timestamp | datetime | Время события |

### ProfileUpdated

Топик: `profile.updated`
Источник: `UserService.update_profile()`

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"profile.updated"` |
| auth_id | UUID | ID учётной записи |
| profile_id | UUID | ID профиля |
| fields_updated | list[str] | Список изменённых полей |
| timestamp | datetime | Время события |

### ProfileDeleted

Топик: `profile.deleted`
Источник: `UserService.delete_profile()`

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"profile.deleted"` |
| auth_id | UUID | ID учётной записи |
| profile_id | UUID | ID профиля |
| timestamp | datetime | Время события |

### TgMessageReceived

Топик: `tg.message.received`
Источник: `TelegramClientManager` (обработчик `on_new_message`)

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"tg.message.received"` |
| account_id | UUID | ID Telegram-аккаунта |
| chat_id | int | ID чата |
| message_id | int | ID сообщения |
| sender_id | int \| null | ID отправителя |
| text | str \| null | Текст сообщения |
| media | list[dict] | Массив media: `[{"type": "photo", "id": "file_id"}]` |
| timestamp | datetime | Время события |

### TgMessageSend

Топик: `tg.message.send`
Источник: Внешние модули (подписка в handlers.py)

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"tg.message.send"` |
| account_id | UUID | ID Telegram-аккаунта |
| chat_id | int | ID чата |
| text | str | Текст сообщения |
| media | list[dict] | Зарезервировано на будущее |

### TgAccountConnected

Топик: `tg.account.connected`
Источник: `TelegramClientService.verify_code()`, `verify_password()`

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"tg.account.connected"` |
| account_id | UUID | ID Telegram-аккаунта |
| auth_id | UUID | ID пользователя |
| phone | str | Номер телефона |
| telegram_id | int \| null | ID в Telegram |
| timestamp | datetime | Время события |

### TgAccountDisconnected

Топик: `tg.account.disconnected`
Источник: `TelegramClientService.delete_account()`

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"tg.account.disconnected"` |
| account_id | UUID | ID Telegram-аккаунта |
| auth_id | UUID | ID пользователя |
| reason | str | Причина: `"manual"`, `"error"`, `"deleted"` |
| timestamp | datetime | Время события |

### NotificationSend

Топик: `notification.send`
Источник: Любой модуль (подписка в notifications/handlers.py)

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"notification.send"` |
| auth_id | UUID | ID пользователя (для резолва email) |
| template_name | str | Имя Jinja2-шаблона |
| channel | str | Канал: `email` (default), `sms` (зарезервировано) |
| body | dict | Переменные для подстановки в шаблон |

### MediaUploaded

Топик: `media.uploaded`
Источник: `MediaService.upload()`

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"media.uploaded"` |
| file_id | UUID | ID загруженного файла |
| filename | str | Оригинальное имя файла |
| content_type | str | MIME-тип |
| size_bytes | int | Размер в байтах |
| is_public | bool | Публичный доступ |
| timestamp | datetime | Время события |

### MediaDeleted

Топик: `media.deleted`
Источник: `MediaService.delete()`

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"media.deleted"` |
| file_id | UUID | ID удалённого файла |
| storage_key | str | Ключ в хранилище |
| timestamp | datetime | Время события |

---

## Диаграмма потоков

```
┌──────────┐                                                    ┌──────────┐
│   auth   │                                                    │  users   │
│  module  │                                                    │  module  │
├──────────┤                                                    ├──────────┤
│          │  publish(user.registered)                          │          │
│ register │ ──────────────────────────────────────────────────▶│ handler  │
│          │                                                    │          │
│          │  publish(user.logged_in)                           │          │
│  login   │ ──────────────────────────────────────────────────▶│ handler  │
│          │                                                    │          │
│          │                                                    │          │
│          │  subscribe(profile.created)                        │  create  │
│          │ ◀──────────────────────────────────────────────────│          │
│          │                                                    │          │
│          │  subscribe(profile.updated)                        │  update  │
│          │ ◀──────────────────────────────────────────────────│          │
│          │                                                    │          │
│          │  subscribe(profile.deleted)                        │  delete  │
│          │ ◀──────────────────────────────────────────────────│          │
└──────────┘                     MessageBus                     └──────────┘

┌──────────────────────┐                                        ┌──────────┐
│  telegram_clients    │                                        │  Любой   │
│  module              │                                        │  модуль  │
├──────────────────────┤                                        ├──────────┤
│                      │  publish(tg.message.received)          │          │
│  ClientManager       │ ─────────────────────────────────────▶│ handler  │
│  (on_new_message)    │                                        │          │
│                      │  publish(tg.account.connected)        │          │
│  Service             │ ─────────────────────────────────────▶│          │
│                      │                                        │          │
│                      │  publish(tg.account.disconnected)     │          │
│                      │ ─────────────────────────────────────▶│          │
│                      │                                        │          │
│                      │  subscribe(tg.message.send)           │  Любой   │
│  ClientManager       │ ◀─────────────────────────────────────│  модуль  │
│  (send_message)      │                                        │          │
└──────────────────────┘                 MessageBus             └──────────┘
```

---

## Как добавить новое событие

1. **Добавьте топик** в `src/core/bus_topics.py`:

```python
class BusTopics:
    # ...
    MY_EVENT: str = "my_module.my_event"
```

2. **Создайте схему события** в `src/modules/my_module/schemas/events.py`:

```python
from src.bus.schemes import BaseEvent
from src.core.bus_topics import BusTopics


class MyEvent(BaseEvent):
    event_name: str = BusTopics.MY_EVENT
    entity_id: uuid.UUID
```

3. **Публикуйте из сервиса**:

```python
event = MyEvent(entity_id=entity.id)
self.message_bus.publish(BusTopics.MY_EVENT, event.to_bus_dict())
```

4. **Подпишите обработчик** в `handlers.py`:

```python
@bus.subscribe(BusTopics.MY_EVENT)
async def handle_my_event(message: dict) -> None:
    logger.info("Событие: %s", message.get("entity_id"))
```

---

# Модели базы данных

## Общие поля

Все модели наследуются от `BaseModel` и автоматически получают:

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID (PK) | Первичный ключ, автогенерация `uuid4` |
| created_at | TIMESTAMP WITH TIME ZONE | Автоматически при INSERT (`server_default=now()`) |
| updated_at | TIMESTAMP WITH TIME ZONE | Автоматически при INSERT и UPDATE (`onupdate=now()`) |

---

## auth_account

Модуль: `src/modules/auth/models.py`

Учётная запись авторизации. Хранит минимум данных для аутентификации.

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| id | UUID | PK, default=uuid4 | Идентификатор |
| email | VARCHAR(255) | UNIQUE, NOT NULL, INDEX | Email пользователя |
| hashed_password | VARCHAR(255) | NOT NULL | Хэш пароля (bcrypt) |
| role | VARCHAR(20) | NOT NULL, DEFAULT 'user' | Роль: `user` или `admin` |
| created_at | TIMESTAMP | NOT NULL | Дата создания |
| updated_at | TIMESTAMP | NOT NULL | Дата обновления |

### Индексы

- `auth_account_email_key` — уникальный индекс по `email`

---

## user_profile

Модуль: `src/modules/users/models.py`

Профиль пользователя. Связан с `auth_account` через `auth_id`, но **без ForeignKey** — модули изолированы.

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| id | UUID | PK, default=uuid4 | Идентификатор профиля |
| auth_id | UUID | UNIQUE, NOT NULL, INDEX | ID учётной записи из модуля auth |
| first_name | VARCHAR(100) | NULLABLE | Имя |
| last_name | VARCHAR(100) | NULLABLE | Фамилия |
| avatar_url | VARCHAR(500) | NULLABLE | URL аватара |
| bio | TEXT | NULLABLE | Описание |
| created_at | TIMESTAMP | NOT NULL | Дата создания |
| updated_at | TIMESTAMP | NOT NULL | Дата обновления |

### Индексы

- `user_profile_auth_id_key` — уникальный индекс по `auth_id`

### Почему нет ForeignKey?

`auth_id` — обычный UUID без `ForeignKey("auth_account.id")`. Это ключевое архитектурное решение:

1. **Изоляция модулей** — каждый модуль может использовать свою БД
2. **Независимое масштабирование** — модуль users не блокирует таблицу auth
3. **Простой вынос в микросервис** — не нужно менять схему при разделении

Ссылочная целостность обеспечивается на уровне бизнес-логики: `auth_id` всегда берётся из JWT-токена, который подписан сервисом авторизации.

---

## telegram_account

Модуль: `src/modules/telegram_clients/models.py`

Telegram-аккаунт пользователя. Связан с `auth_account` через `auth_id` без ForeignKey.

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| id | UUID | PK, default=uuid4 | Идентификатор аккаунта |
| auth_id | UUID | NOT NULL, INDEX | ID пользователя из модуля auth (без FK) |
| phone | VARCHAR(20) | NOT NULL | Номер телефона |
| session_file | VARCHAR(500) | NOT NULL | Путь к SQLite session-файлу Telethon |
| is_connected | BOOLEAN | DEFAULT FALSE | Подключён ли сейчас |
| first_name | VARCHAR(100) | NULLABLE | Имя из Telegram |
| last_name | VARCHAR(100) | NULLABLE | Фамилия из Telegram |
| username | VARCHAR(100) | NULLABLE | Username |
| telegram_id | BIGINT | NULLABLE | ID в Telegram (заполняется после авторизации) |
| created_at | TIMESTAMP | NOT NULL | Дата создания |
| updated_at | TIMESTAMP | NOT NULL | Дата обновления |

### Индексы

- `ix_telegram_account_auth_id` — индекс по `auth_id`

---

## notification_template

Модуль: `src/modules/notifications/models.py`

Шаблон уведомления (Jinja2). Хранится в БД, может переопределять файловые шаблоны.

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| id | UUID | PK, default=uuid4 | Идентификатор |
| name | VARCHAR(100) | UNIQUE, NOT NULL | Имя шаблона (`welcome`, `password_reset`) |
| channel | VARCHAR(20) | NOT NULL | Канал: `email`, `sms` |
| subject_template | TEXT | NULLABLE | Jinja2-шаблон темы (для email) |
| body_template | TEXT | NOT NULL | Jinja2-шаблон тела |
| is_active | BOOLEAN | DEFAULT TRUE | Включён ли шаблон |
| created_at | TIMESTAMP | NOT NULL | Дата создания |
| updated_at | TIMESTAMP | NOT NULL | Дата обновления |

---

## notification_log

Модуль: `src/modules/notifications/models.py`

Лог отправленного уведомления. Хранит статус, отрендеренный текст и ошибки.

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| id | UUID | PK, default=uuid4 | Идентификатор |
| auth_id | UUID | NOT NULL, INDEX | ID пользователя (без FK) |
| channel | VARCHAR(20) | NOT NULL | `email`, `sms` |
| template_name | VARCHAR(100) | NOT NULL | Имя использованного шаблона |
| recipient | VARCHAR(255) | NOT NULL | Email/телефон получателя |
| subject | TEXT | NULLABLE | Отрендеренная тема |
| body | TEXT | NOT NULL | Отрендеренное тело |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'pending' | `pending`, `sent`, `failed` |
| error_message | TEXT | NULLABLE | Ошибка (если failed) |
| created_at | TIMESTAMP | NOT NULL | Дата создания |
| updated_at | TIMESTAMP | NOT NULL | Дата обновления |

### Индексы

- `ix_notification_log_auth_id` — индекс по `auth_id`

---

## ER-диаграмма

```
┌──────────────────┐          ┌──────────────────────┐
│   auth_account   │          │    user_profile      │
├──────────────────┤          ├──────────────────────┤
│ id (UUID, PK)    │◄─ ─ ─ ─ │ auth_id (UUID, UQ)   │
│ email (UQ)       │  логич.  │ first_name           │
│ hashed_password  │  связь   │ last_name            │
│ role             │          │ avatar_url           │
│ created_at       │          │ bio                  │
│ updated_at       │          │ created_at           │
└──────────────────┘          │ updated_at           │
        │                     └──────────────────────┘
        │
        │  ┌──────────────────────────┐
        │  │    telegram_account      │
        │  ├──────────────────────────┤
        └──│ auth_id (UUID, INDEX)    │
           │ phone                    │
           │ session_file             │
           │ is_connected             │
           │ first_name               │
           │ last_name                │
           │ username                 │
           │ telegram_id (BIGINT)     │
           │ created_at               │
           │ updated_at               │
           └──────────────────────────┘
        │
        │  ┌──────────────────────────┐
        │  │    notification_log      │
        │  ├──────────────────────────┤
        └──│ auth_id (UUID, INDEX)    │
           │ channel                  │
           │ template_name            │
           │ recipient                │
           │ subject                  │
           │ body                     │
           │ status                   │
           │ error_message            │
           │ created_at               │
           │ updated_at               │
           └──────────────────────────┘

  ┌──────────────────────────┐
  │ notification_template    │
  ├──────────────────────────┤
  │ id (UUID, PK)            │
  │ name (UQ)                │
  │ channel                  │
  │ subject_template         │
  │ body_template            │
  │ is_active                │
  │ created_at               │
  │ updated_at               │
  └──────────────────────────┘

  ─ ─ ─  логическая связь (без ForeignKey)
```

---

## stored_file

Модуль: `src/modules/media/models.py`

Медиа-файл. Файлы независимы — не имеют владельца (`auth_id`), доступ контролируется через `is_public`.

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| id | UUID | PK, default=uuid4 | Идентификатор файла |
| filename | VARCHAR(255) | NOT NULL | Оригинальное имя файла |
| content_type | VARCHAR(100) | NOT NULL | MIME-тип (image/png, application/pdf) |
| size_bytes | BIGINT | NOT NULL | Размер в байтах |
| storage_key | VARCHAR(500) | UNIQUE, NOT NULL | Ключ в хранилище (ab/cd/uuid.ext) |
| is_public | BOOLEAN | DEFAULT FALSE | Публичный доступ |
| created_at | TIMESTAMP | NOT NULL | Дата загрузки |
| updated_at | TIMESTAMP | NOT NULL | Дата обновления |

### Индексы

- `stored_file_storage_key_key` — уникальный индекс по `storage_key`

### Почему нет владельца?

Файлы спроектированы как независимые ресурсы для упрощения межмодульного доступа:

1. **Межмодульное взаимодействие** — любой модуль может получить файл через `/internal/media/{id}`
2. **Упрощённая модель** — не нужно проверять права владельца при доступе
3. **Гибкость** — `is_public` контролирует публичный доступ, network-level — внутренний

При необходимости связи "файл-владелец" создаётся отдельная таблица-связка в модуле-потребителе.

---

# Запуск и развёртывание

## Локальная разработка

### Установка

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Настройка окружения

```bash
cp .env.example .env
```

Отредактируйте `.env`:

```env
# Обязательно укажите реальный URL БД и секретный ключ
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/modular_monolith
JWT_SECRET_KEY=your-secret-key-here
```

### Запуск

```bash
uvicorn src.main:app --reload
```

- Приложение: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Тесты

```bash
pytest tests/ -v
```

Тесты используют SQLite в памяти — не требуют PostgreSQL.

### Линтинг

```bash
ruff check src/ tests/
```

Автофикс:

```bash
ruff check src/ tests/ --fix
```

---

## Переменные окружения

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | URL подключения к PostgreSQL |
| `DATABASE_POOL_SIZE` | `5` | Размер пула подключений |
| `JWT_SECRET_KEY` | — | Секретный ключ для JWT (**обязательно сменить!**) |
| `JWT_ALGORITHM` | `HS256` | Алгоритм подписи JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Время жизни токена (минуты) |
| `MESSAGE_BUS` | `in_memory` | Реализация шины: `in_memory` или `kafka` |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Адрес Kafka-брокера |
| `KAFKA_GROUP_ID` | `modular-monolith` | ID consumer group Kafka |
| `APP_TITLE` | `Modular Monolith` | Название приложения в Swagger |
| `DEBUG` | `false` | Режим отладки (SQL-логирование) |
| `TG_API_ID` | `0` | API ID из my.telegram.org (**обязательно для Telegram**) |
| `TG_API_HASH` | — | API Hash из my.telegram.org (**обязательно для Telegram**) |
| `TG_SESSION_DIR` | `sessions` | Директория для хранения session-файлов Telethon |
| `SMTP_HOST` | `localhost` | SMTP сервер |
| `SMTP_PORT` | `587` | Порт SMTP |
| `SMTP_USERNAME` | — | Логин SMTP |
| `SMTP_PASSWORD` | — | Пароль SMTP |
| `SMTP_USE_TLS` | `true` | Использовать TLS |
| `SMTP_FROM_EMAIL` | `noreply@example.com` | Email отправителя |
| `SMTP_FROM_NAME` | `App` | Имя отправителя |
| `TEMPLATES_DIR` | `templates` | Директория файловых Jinja2-шаблонов |
| `MEDIA_STORAGE_PROVIDER` | `local` | Провайдер хранилища: `local` (LocalStorage), `s3` (будущее) |
| `MEDIA_STORAGE_PATH` | `uploads` | Директория для хранения файлов |
| `MEDIA_MAX_SIZE_MB` | `5` | Максимальный размер файла (MB) |

---

## Переключение на Kafka

### 1. Запустите Kafka

```bash
# Docker Compose (пример)
docker-compose up -d kafka zookeeper
```

### 2. Обновите `.env`

```env
MESSAGE_BUS=kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_GROUP_ID=modular-monolith
```

### 3. Перезапустите приложение

```bash
uvicorn src.main:app --reload
```

При `MESSAGE_BUS=kafka` приложение автоматически использует:
- `KafkaProducerBus` вместо `InMemoryProducer`
- `KafkaConsumerRouter` вместо `InMemoryConsumer`

Бизнес-логика модулей **не меняется** — они зависят от интерфейса `MessageBus`.

---

## Вынос модуля в микросервис

Когда модуль нужно выделить в отдельный сервис:

### 1. Скопируйте модуль

Скопируйте `src/modules/<module_name>/` в новый проект.

### 2. Скопируйте общие абстракции

В новый проект понадобятся:
- `src/base/` — BaseModel, BaseRepository, BaseService
- `src/core/config.py` — Settings
- `src/core/database.py` — подключение к БД
- `src/core/exceptions.py` — исключения
- `src/core/security.py` — JWT (если нужно)
- `src/bus/` — шина сообщений

### 3. Замените InMemory на Kafka

В новом сервисе установите `MESSAGE_BUS=kafka`. Модуль уже умеет работать с Kafka — ничего менять не нужно.

### 4. Обновите DI-контейнер

Создайте собственный `dependencies.py` в новом сервисе. Если модуль обращался к данным другого модуля — замените репозиторий на HTTP-клиент:

```python
# Было (монолит):
class UserRepository(BaseRepository[User]):
    async def get_by_auth_id(self, session, auth_id): ...

# Стало (микросервис):
class UserHTTPClient:
    def __init__(self, http_client: httpx.AsyncClient):
        self._client = http_client

    async def get_by_auth_id(self, _, auth_id):
        response = await self._client.get(f"/users/{auth_id}")
        return response.json()
```

### 5. Обновите main.py

Подключите только нужные роутеры и обработчики:

```python
app = FastAPI(lifespan=lifespan)
app.include_router(my_module_router, prefix="/my-module", tags=["MyModule"])
```

### Что НЕ меняется

- **Бизнес-логика** в `service.py` — остаётся без изменений
- **События** — топики и форматы те же самые
- **API-схемы** — Pydantic-модели те же
- **Обработчики** — подписки на шину те же

---

## Настройка Telegram-модуля

### 1. Получите API credentials

1. Перейдите на [my.telegram.org](https://my.telegram.org)
2. Создайте приложение → получите `API ID` и `API Hash`

### 2. Укажите в `.env`

```env
TG_API_ID=12345678
TG_API_HASH=your_api_hash_here
TG_SESSION_DIR=sessions
```

### 3. Запустите приложение

При старте приложение:
- Создаёт директорию `sessions/` (если не существует)
- Подключает все ранее авторизованные Telegram-аккаунты
- Начинает слушать входящие сообщения

### Восстановление сессий

При перезапуске приложения все аккаунты с `is_connected=True` автоматически подключаются из session-файлов. Если сессия устарела — аккаунт помечается как отключённый.

---

# Универсальная фильтрация запросов

## Обзор

Модуль `src/base/filters.py` предоставляет механизм универсальной фильтрации для SQLAlchemy-запросов. Используется в внутренних роутах (`/internal/`) для динамической фильтрации данных без хардкода условий в коде.

## Расположение

```
src/base/filters.py
```

> **Примечание:** Файл находится в `src/base/`, а не в `src/core/`, как указано в некоторых местах документации.

## Архитектура

### Операторы фильтрации

Поддерживаемые операторы определены в `FilterOperator`:

| Оператор | Описание | Пример |
|----------|----------|--------|
| `eq` | Равно (`=`) | `auth_id+eq+550e8400-...` |
| `ne` | Не равно (`!=`) | `status+ne+deleted` |
| `gt` | Больше (`>`) | `age+gt+18` |
| `ge` | Больше или равно (`>=`) | `age+ge+18` |
| `lt` | Меньше (`<`) | `age+lt+65` |
| `le` | Меньше или равно (`<=`) | `age+le+65` |
| `like` | LIKE (регистрозависимый) | `name+like+%test%` |
| `ilike` | ILIKE (регистронезависимый) | `name+ilike+%ivan%` |
| `in` | В списке | `status+in+active,pending` |

### Структура данных

#### `Filter`

Pydantic-модель, представляющая один фильтр:

```python
class Filter(PydanticModel):
    field: str                # Имя поля модели
    operator: FilterOperator  # Оператор сравнения
    value: str                # Значение (для IN — строка через запятую)
```

## API

### `parse_filters(raw: list[str]) -> list[Filter]`

Парсит список строк формата `field+operator+value` в объекты `Filter`.

**Параметры:**
- `raw` — список строк, например: `["auth_id+eq+uuid", "email+ilike+%test%"]`

**Возвращает:**
- Список объектов `Filter`
- Некорректные строки silently пропускаются

**Пример:**
```python
raw_filters = ["auth_id+eq+550e8400-e29b-41d4-a716-446655440000", "email+ilike+%test%"]
filters = parse_filters(raw_filters)
# Результат: [Filter(field="auth_id", operator=FilterOperator.EQ, value="550e8400-..."), ...]
```

### `apply_filters(stmt: Select, model: type, filters: list[Filter]) -> Select`

Применяет список фильтров к SQLAlchemy `select()`-запросу.

**Параметры:**
- `stmt` — исходный SQLAlchemy select-запрос
- `model` — SQLAlchemy модель (для доступа к полям)
- `filters` — список объектов `Filter`

**Возвращает:**
- Модифицированный select-запрос (immutable pattern)

**Особенности:**
- Неизвестные поля модели silently пропускаются
- Возвращает новый объект запроса (не мутирует исходный)

**Пример:**
```python
from sqlalchemy import select
from src.modules.users.models import User
from src.base.filters import parse_filters, apply_filters

# Исходный запрос
stmt = select(User)

# Применяем фильтры
raw = ["auth_id+eq+550e8400-e29b-41d4-a716-446655440000"]
filters = parse_filters(raw)
stmt = apply_filters(stmt, User, filters)

# Выполняем
result = await session.execute(stmt)
```

## Использование в роутах

Все роуты, возвращающие списки, поддерживают фильтрацию через параметр `filters`:

### Пример: `/internal/users/`

```python
from fastapi import APIRouter
from sqlalchemy import select
from src.core.database import get_db_session
from src.modules.users.models import User
from src.base.filters import parse_filters, apply_filters

router = APIRouter(prefix="/internal/users", tags=["Internal Users"])


@router.get("/")
async def get_users(
    filters: list[str] = Query(default_factory=list, description="field+operator+value"),
    db_session=Depends(get_db_session),
):
    stmt = select(User)

    # Применяем фильтры
    if filters:
        parsed_filters = parse_filters(filters)
        stmt = apply_filters(stmt, User, parsed_filters)

    result = await db_session.execute(stmt)
    users = result.scalars().all()

    return users
```

**Запрос:**
```
GET /internal/users/?filters=auth_id+eq+550e8400-...&filters=email+ilike+%test%
```

### Доступные эндпоинты с фильтрацией

| Модуль | Эндпоинт | Описание |
|--------|----------|----------|
| **users** | `GET /internal/users/` | Список пользователей |
| **media** | `GET /internal/media/` | Список файлов |
| **notifications** | `GET /notifications/templates/` | Список шаблонов уведомлений |
| **notifications** | `GET /notifications/history/` | История отправленных уведомлений |
| **telegram_clients** | `GET /telegram/` | Список Telegram-аккаунтов пользователя |

**Примеры запросов:**

```bash
# Фильтрация файлов по имени
GET /internal/media/?filters=filename+like+report

# Фильтрация шаблонов по типу канала
GET /notifications/templates/?filters=channel+eq+email

# Фильтрация аккаунтов по статусу подключения
GET /telegram/?filters=is_connected+eq+true

# Комбинированная фильтрация
GET /internal/media/?filters=is_public+eq+true&filters=filename+like+doc
```

## Тестирование

Фильтры легко тестируются благодаря чистым функциям:

```python
from src.base.filters import parse_filters, apply_filters, FilterOperator


def test_parse_filters():
    raw = ["age+gt+18", "status+eq+active"]
    result = parse_filters(raw)

    assert len(result) == 2
    assert result[0].field == "age"
    assert result[0].operator == FilterOperator.GT
    assert result[0].value == "18"


def test_apply_filters():
    from src.modules.users.models import User
    from sqlalchemy import select

    stmt = select(User)
    filters = parse_filters(["auth_id+eq+550e8400-..."])
    stmt = apply_filters(stmt, User, filters)

    # Проверка сгенерированного SQL
    print(stmt)  # SELECT ... WHERE auth_id = :param_1
```

## Особенности реализации

### Обработка `IN` оператора

Значение для `in` передаётся как строка через запятую:

```python
# Вход
"status+in+active,pending,deleted"

# Парсинг
Filter(field="status", operator=FilterOperator.IN, value="active,pending,deleted")

# Применение
col.in_("active,pending,deleted".split(","))  # ['active', 'pending', 'deleted']
```

### Silent пропуск ошибок

- Некорректные строки в `parse_filters` пропускаются без ошибки
- Неизвестные поля модели в `apply_filters` пропускаются без ошибки

Это позволяет использовать фильтры в API без риска 500-х ошибок при некорректном запросе.

### Типы значений

Все значения передаются как `str`. Преобразование типов происходит неявно:
- UUID — как строка (совпадает с SQLAlchemy)
- Числа — SQLAlchemy автоматически конвертирует
- Даты — как ISO 8601 строки

## Интеграция с Pydantic

`Filter` использует Pydantic v2 для валидации:

```python
from pydantic import TypeAdapter
from src.base.filters import Filter

adapter = TypeAdapter(list[Filter])
data = [
    {"field": "age", "operator": "gt", "value": "18"},
    {"field": "status", "operator": "eq", "value": "active"}
]
filters = adapter.validate_python(data)
```

## См. также

- [Архитектура](architecture.md) — раздел "Фильтрация"
- [Internal API](api.md#internal) — использование фильтров в `/internal/` роутах
- [BaseRepository](architecture.md#слои-внутри-модуля) — где применяется фильтрация

---

# Правила изоляции модулей

## Зачем нужна изоляция

Модульная изоляция — фундамент Modular Monolith. Она гарантирует, что:

1. Модули можно разрабатывать и тестировать независимо
2. Модуль можно вынести в микросервис без переписывания
3. Изменения в одном модуле не ломают другой
4. Команда может работать над модулем автономно

---

## ✅ Разрешено

| Действие | Пример |
|----------|--------|
| Импорт из `src.base.*` | `from src.base.model import BaseModel` |
| Импорт из `src.core.*` | `from src.core.config import settings` |
| Импорт из `src.bus.*` | `from src.bus.interface import MessageBus` |
| Импорт из собственного модуля | `from src.modules.auth.models import Auth` (внутри auth) |
| Публикация событий через шину | `self.message_bus.publish(BusTopics.USER_REGISTERED, ...)` |
| Подписка на события через шину | `@bus.subscribe(BusTopics.PROFILE_CREATED)` |
| Использование `Protocol` для интерфейсов | `class UserCreator(Protocol)` |
| Передача ID другого модуля как аргумент | `auth_id: uuid.UUID` из JWT |

---

## ❌ Запрещено

| Действие | Почему |
|----------|--------|
| Прямой импорт модели другого модуля | `from src.modules.auth.models import Auth` из users — **нельзя** |
| Прямой импорт сервиса другого модуля | `from src.modules.auth.service import AuthService` из users — **нельзя** |
| Прямой импорт репозитория другого модуля | Жёсткая связанность, невозможно вынести модуль |
| ForeignKey на таблицу другого модуля | Модули не могут жить в разных БД |
| Общие таблицы между модулями | Нарушает принцип единого владельца данных |
| Хардкод строк топиков | `"user.registered"` — опечатки, нет автодополнения |
| Передача auth_id в схеме Create | ID из другого модуля — аргумент метода, не поле формы |

---

## Как модули общаются

### Паттерн: Event-Driven Architecture

```
┌─────────────┐    publish("user.registered")    ┌─────────────┐
│    auth      │ ───────────────────────────────▶ │    users     │
│   module     │                                  │   module     │
│             │ ◀───────────────────────────────── │             │
└─────────────┘    subscribe("profile.updated")   └─────────────┘
                         MessageBus
```

1. **Модуль A** публикует событие в шину через `message_bus.publish()`
2. **Модуль B** подписан на топик через `@bus.subscribe()`
3. Ни один модуль не знает о внутреннем устройстве другого

### Паттерн: Protocol (интерфейс)

Если модулю нужно вызвать метод другого модуля напрямую:

```python
# В модуле auth: определяем интерфейс
class UserCreator(Protocol):
    async def create_user_profile(self, session, auth_id: UUID) -> None: ...

# В модуле users: реализуем интерфейс
class UserService(BaseService):
    async def create_user_profile(self, session, auth_id: UUID) -> None: ...

# В dependencies.py: связываем через DI
def get_auth_service(
    user_creator: UserCreator = Depends(get_user_service),
) -> AuthService: ...
```

Модуль auth зависит от абстракции `UserCreator`, а не от конкретного `UserService`.

---

## Правила для БД

### Один модуль — один владелец таблицы

Каждая таблица принадлежит ровно одному модулю. Только этот модуль:
- Читает из таблицы
- Пишет в таблицу
- Определяет схему и миграции

### Нет ForeignKey между модулями

```
❌ Плохо:
auth_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth.id"))

✅ Хорошо:
auth_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
```

Ссылочная целостность обеспечивается на уровне бизнес-логики, а не СУБД.

### Нет общих таблиц

Если двум модулям нужны одни и те же данные — они дублируются или передаются через события. Это цена изоляции.

---

## Правила для шины сообщений

### Топики — только из BusTopics

```python
❌ Плохо:
self.message_bus.publish("user.registered", data)

✅ Хорошо:
self.message_bus.publish(BusTopics.USER_REGISTERED, data)
```

### Обработчики — идемпотентные

Событие может быть доставлено повторно (особенно в Kafka). Обработчик должен быть безопасен при повторном вызове.

### Обработчики — без прямых импортов

```python
❌ Плохо:
from src.modules.auth.service import AuthService

@bus.subscribe(BusTopics.USER_REGISTERED)
async def handle(message):
    auth_service = AuthService(...)  # прямая связь!

✅ Хорошо:
@bus.subscribe(BusTopics.USER_REGISTERED)
async def handle(message):
    logger.info("Пользователь: %s", message.get("auth_id"))
```

---

## Визуальная проверка изоляции

Если в `src/modules/users/` есть импорт из `src/modules/auth/` (кроме Protocol) — **изоляция нарушена**.

Проверка одной командой:

```bash
# Должно вернуть пустой результат
grep -r "from src.modules.auth" src/modules/users/
grep -r "from src.modules.users" src/modules/auth/
```

---

# Как добавить новый модуль

Пошаговый гайд по созданию нового бизнес-модуля.

---

## Шаг 1. Создайте структуру директорий

```
src/modules/<module_name>/
├── __init__.py
├── models.py          # SQLAlchemy-модель
├── schemas/
│   ├── __init__.py
│   ├── api.py         # Pydantic-схемы для HTTP
│   └── events.py      # Pydantic-схемы для событий шины
├── repository.py      # Репозиторий (наследуется от BaseRepository)
├── service.py         # Сервис (наследуется от BaseService)
├── handlers.py        # Обработчики событий шины (опционально)
└── router.py          # FastAPI-роутер
```

---

## Шаг 2. Определите топики в BusTopics

**До создания событий** — добавьте топики в `src/core/bus_topics.py`:

```python
class BusTopics:
    # ... существующие топики ...

    # Модуль MyModule
    MY_ENTITY_CREATED: str = "my_entity.created"
    MY_ENTITY_UPDATED: str = "my_entity.updated"
    MY_ENTITY_DELETED: str = "my_entity.deleted"
```

---

## Шаг 3. Определите модель (`models.py`)

```python
import uuid
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from src.base.model import BaseModel


class MyEntity(BaseModel):
    __tablename__ = "my_entity"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Ссылка на другой модуль — обычный UUID, без ForeignKey!
    auth_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
```

**Правила:**
- Наследуйтесь от `BaseModel` (даёт `id`, `created_at`, `updated_at`)
- **Никогда** не создавайте ForeignKey на таблицы других модулей
- Ссылки на другие модули — обычные UUID-поля

---

## Шаг 4. Определите API-схемы (`schemas/api.py`)

```python
import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class MyEntityCreate(BaseModel):
    """Поля для создания. auth_id НЕ включаем — он из JWT."""
    name: str = Field(max_length=255)


class MyEntityRead(BaseModel):
    """Полная схема для ответа."""
    id: uuid.UUID
    auth_id: uuid.UUID
    name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MyEntityUpdate(BaseModel):
    """Partial update — все поля опциональны."""
    name: str | None = Field(default=None, max_length=255)
```

**Правила:**
- `Create` — поля для создания (без `id`, без `auth_id` из других модулей)
- `Read` — полная схема с `model_config = {"from_attributes": True}`
- `Update` — все поля опциональны (partial update)
- `auth_id` и другие ID из других модулей — **не в схеме**, передаются как аргументы

---

## Шаг 5. Определите события (`schemas/events.py`)

```python
import uuid
from src.bus.schemes import BaseEvent
from src.core.bus_topics import BusTopics


class MyEntityCreated(BaseEvent):
    event_name: str = BusTopics.MY_ENTITY_CREATED
    entity_id: uuid.UUID
    auth_id: uuid.UUID


class MyEntityUpdated(BaseEvent):
    event_name: str = BusTopics.MY_ENTITY_UPDATED
    entity_id: uuid.UUID
    fields_updated: list[str]


class MyEntityDeleted(BaseEvent):
    event_name: str = BusTopics.MY_ENTITY_DELETED
    entity_id: uuid.UUID
```

**Правила:**
- Наследуйтесь от `BaseEvent` (даёт `timestamp` и метод `to_bus_dict()`)
- `event_name` берите из `BusTopics` — **не хардкодите строки**

---

## Шаг 6. Создайте репозиторий (`repository.py`)

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.base.repository import BaseRepository
from src.modules.my_module.models import MyEntity


class MyEntityRepository(BaseRepository[MyEntity]):
    def __init__(self) -> None:
        super().__init__(MyEntity)

    async def get_by_name(
        self, session: AsyncSession, name: str
    ) -> MyEntity | None:
        stmt = select(MyEntity).where(MyEntity.name == name)
        result = await session.execute(stmt)
        return result.scalars().first()
```

`BaseRepository` уже предоставляет: `get_by_id`, `get_all`, `create`, `update`, `delete`.

---

## Шаг 7. Создайте сервис (`service.py`)

```python
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from src.base.service import BaseService
from src.bus.interface import MessageBus
from src.core.bus_topics import BusTopics
from src.core.exceptions import NotFoundError
from src.modules.my_module.repository import MyEntityRepository
from src.modules.my_module.schemas.api import MyEntityCreate, MyEntityUpdate
from src.modules.my_module.schemas.events import MyEntityCreated


class MyEntityService(BaseService[MyEntityRepository]):
    def __init__(
        self, repository: MyEntityRepository, message_bus: MessageBus
    ) -> None:
        super().__init__(repository)
        self.message_bus = message_bus

    async def create_entity(
        self, session: AsyncSession, data: MyEntityCreate, auth_id: uuid.UUID
    ) -> None:
        """auth_id пробрасывается из JWT, а не из схемы."""
        values = data.model_dump(exclude_unset=True)
        values["auth_id"] = auth_id
        entity = await self.repository.create(session, values)

        event = MyEntityCreated(entity_id=entity.id, auth_id=auth_id)
        self.message_bus.publish(BusTopics.MY_ENTITY_CREATED, event.to_bus_dict())

    async def get_entity(self, session: AsyncSession, auth_id: uuid.UUID):
        entity = await self.repository.get_by_auth_id(session, auth_id)
        if not entity:
            raise NotFoundError(detail="Сущность не найдена")
        return entity
```

**Правила:**
- `auth_id` и другие ID из других модулей — **передавайте как аргументы**, не из схемы
- Публикуйте события **после** успешной операции
- Используйте `BusTopics` для имён топиков

---

## Шаг 8. Создайте обработчики (`handlers.py`)

```python
import logging
from src.bus.interface import MessageBus
from src.core.bus_topics import BusTopics

logger = logging.getLogger(__name__)


def register_handlers(bus: MessageBus) -> None:
    @bus.subscribe(BusTopics.USER_REGISTERED)
    async def handle_user_registered(message: dict) -> None:
        logger.info("Новый пользователь: %s", message.get("auth_id"))

    @bus.subscribe(BusTopics.PROFILE_UPDATED)
    async def handle_profile_updated(message: dict) -> None:
        logger.info("Профиль обновлён: %s", message.get("auth_id"))
```

**Правила:**
- Подписывайтесь только на топики из `BusTopics`
- Обработчики должны быть **идемпотентными** (безопасными при повторном вызове)
- Не делайте прямых импортов из других модулей

---

## Шаг 9. Создайте роутер (`router.py`)

```python
import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.dependencies import get_current_user, get_db_session
from src.modules.my_module.dependencies import get_my_entity_service
from src.modules.my_module.schemas.api import MyEntityCreate, MyEntityRead
from src.modules.my_module.service import MyEntityService

router = APIRouter()


@router.post(
    "/",
    response_model=MyEntityRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_entity(
    data: MyEntityCreate,
    auth_id: uuid.UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: MyEntityService = Depends(get_my_entity_service),
) -> MyEntityRead:
    await service.create_entity(session, data, auth_id)
    return await service.get_entity(session, auth_id)
```

---

## Шаг 10. Создайте файл зависимостей (`dependencies.py`)

Создайте `src/modules/<module_name>/dependencies.py` — **не в `core/dependencies.py`**:

```python
"""
DI-зависимости модуля <module_name>.

Фабрики для внедрения сервиса через FastAPI Depends.
"""

from fastapi import Depends
from src.bus.interface import MessageBus
from src.bus.providers import get_message_bus
from src.modules.my_module.repository import MyEntityRepository
from src.modules.my_module.service import MyEntityService


def get_my_entity_repository() -> MyEntityRepository:
    return MyEntityRepository()


def get_my_entity_service(
    repo: MyEntityRepository = Depends(get_my_entity_repository),
    bus: MessageBus = Depends(get_message_bus),
) -> MyEntityService:
    return MyEntityService(repository=repo, message_bus=bus)
```

**Почему в модуле, а не в `core/dependencies.py`?**
- Модули изолированы — ядро не знает о модулях
- При выносе в микросервис — `dependencies.py` переезжает вместе с модулем
- `src/core/dependencies.py` содержит только **общие** зависимости (БД, JWT)

---

## Шаг 11. Подключите роутер в `main.py`

```python
from src.modules.my_module.router import router as my_module_router

app.include_router(my_module_router, prefix="/my-module", tags=["MyModule"])
```

---

## Шаг 12. Зарегистрируйте обработчики в `main.py`

```python
from src.modules.my_module.handlers import register_handlers as register_my_module_handlers

register_my_module_handlers(producer)
```

---

## Чеклист

- [ ] Структура директорий создана
- [ ] Топики добавлены в `BusTopics`
- [ ] Модель определена (без ForeignKey на другие модули)
- [ ] API-схемы определены (auth_id не в Create-схеме)
- [ ] События определены (event_name из BusTopics)
- [ ] Репозиторий создан (наследуется от BaseRepository)
- [ ] Сервис создан (наследуется от BaseService, принимает MessageBus)
- [ ] Обработчики событий созданы (опционально)
- [ ] Роутер создан (auth_id через Depends)
- [ ] Зависимости зарегистрированы в `dependencies.py`
- [ ] Роутер подключён в `main.py`
- [ ] Обработчики зарегистрированы в `main.py`
- [ ] Тесты написаны

---

*Документация объединена: вторник, 7 июля 2026 г.*
