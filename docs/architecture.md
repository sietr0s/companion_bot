# Архитектура

## Обзор

Сервис построен по принципу **Modular Monolith** — приложение состоит из изолированных модулей, работающих в одном процессе. Каждый модуль спроектирован так, чтобы в будущем его можно было вынести в отдельный микросервис **без переписывания бизнес-логики**.

## Принципы

| Принцип | Описание |
|---------|----------|
| **Изоляция модулей** | Модули не импортируют друг друга напрямую |
| **Связь через шину** | Асинхронное взаимодействие — через `MessageProducer` / `MessageConsumer` |
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
│   ├── interface.py             # MessageProducer и MessageConsumer (Protocol)
│   ├── schemes.py               # BaseEvent — базовый класс событий
│   ├── in_memory/               # In-memory реализация (для монолита)
│   │   ├── transport.py         # Общая asyncio.Queue
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
│   │   └── routers/             # Public и internal API с собственными префиксами
│   │
│   └── users/                   # Модуль пользователей
│       ├── models.py            # User (auth_id, first_name, last_name, avatar_url, bio), Telegram
│       ├── schemas/public/user.py       # UserCreate, UserRead, UserUpdate
│       ├── schemas/internal/user.py     # UserCreate, UserRead, UserUpdate
│       ├── schemas/events.py    # ProfileCreated, ProfileUpdated, ProfileDeleted
│       ├── repository.py        # UserRepository (+ get_by_auth_id), TelegramRepository
│       ├── service.py           # UserService (create, get, update, delete)
│       ├── handlers.py          # Обработчики событий из шины
│       └── routers/             # Public и internal API с собственными префиксами
│
│   └── telegram_clients/        # Модуль Telegram-клиентов
│       ├── models.py            # TelegramAccount (auth_id, phone, session_file, is_connected, ...)
│       ├── schemas/public/      # Публичные Pydantic-схемы
│       ├── schemas/internal/    # Internal Pydantic-схемы
│       ├── schemas/events.py    # TgMessageReceived, TgMessageSend, TgAccountConnected, TgAccountDisconnected
│       ├── repository.py        # TelegramAccountRepository (+ get_by_auth_id, get_connected_accounts)
│       ├── client_manager.py    # TelegramClientManager — singleton управления Telethon-клиентами
│       ├── service.py           # TelegramClientService (auth, CRUD, chats, messages)
│       ├── handlers.py          # Подписка на tg.message.send
│       └── routers/             # Public и internal API Telegram
│
│   └── notifications/           # Модуль нотификаций
│       ├── models.py            # NotificationTemplate, NotificationLog
│       ├── schemas/public/      # TemplateCreate, TemplateRead, NotificationLogRead
│       ├── schemas/internal/    # SendNotificationRequest
│       ├── schemas/events.py    # NotificationSend
│       ├── repository.py        # NotificationTemplateRepository, NotificationLogRepository
│       ├── providers/           # Абстракция провайдеров (Protocol + SMTP)
│       │   ├── base.py          # NotificationProvider (Protocol)
│       │   └── smtp.py          # SmtpProvider (aiosmtplib)
│       ├── template_engine.py   # Jinja2 рендеринг (БД → файлы)
│       ├── service.py           # NotificationService (шаблоны, отправка, история)
│       ├── handlers.py          # Подписка на notification.send
│       └── routers/             # Public и internal API notifications
│
│   └── media/                   # Модуль медиа-файлов
│       ├── models.py            # StoredFile (id, filename, content_type, size_bytes, storage_key, is_public)
│       ├── schemas/             # HTTP-схемы и события
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
├── core/container.py            # Явный контейнер долгоживущих компонентов
└── main.py                      # Composition root и фабрика create_app()
```

## Слои внутри модуля

Каждый модуль следует трёхслойной архитектуре:

```
Router (HTTP) → Service (бизнес-логика) → Repository (БД)
     │                  │
     │                  └──→ MessageProducer (события)
     │
     └──→ Depends (DI-контейнер)
```

- **Router** — принимает HTTP-запросы, валидирует через Pydantic, вызывает сервис
- **Service** — содержит бизнес-логику, публикует события, не знает про HTTP
- **Repository** — работает с SQLAlchemy, не знает про бизнес-логику

### Работа сервисов с БД

**Важное правило:** Сервисы **НЕ должны** напрямую работать с сессией БД (`session.add()`, `session.commit()`, `session.refresh()`, `session.execute()`). Все операции с БД делегируются репозиторию.

**Правильно:**
```python
class UserService(BaseService[UserRepository, User]):
    async def create_profile(self, session: AsyncSession, auth_id: UUID, data: dict):
        # ✅ Создание через репозиторий
        profile = await self.repository.create(session, {"auth_id": auth_id, **data})
        
        # ✅ Обновление через репозиторий
        await self.repository.update(session, profile, {"first_name": "Имя"})
        
        # ✅ Получение через репозиторий
        existing = await self.repository.get_by_id(session, profile_id)
        
        return profile
```

**Неправильно:**
```python
class UserService(BaseService[UserRepository, User]):
    async def create_profile(self, session: AsyncSession, auth_id: UUID, data: dict):
        # ❌ Прямая работа с сессией
        profile = User(auth_id=auth_id, **data)
        session.add(profile)      # ❌
        await session.commit()    # ❌
        await session.refresh(profile)  # ❌
        return profile
```

**Базовые методы репозитория (из `BaseRepository`):**
- `create(session, data_dict)` — создание
- `get_by_id(session, id)` — получение по ID
- `update(session, obj, data_dict)` — обновление
- `delete(session, obj)` — удаление
- `get_all(session, skip, limit)` — список с пагинацией
- `get_list(session, filters, ...)` — список с фильтрами
- `count(session, filters)` — подсчёт записей

Если нужна сложная логика сохранения — создайте кастомный метод в репозитории, не в сервисе.

## Особенность: ClientManager

Модуль `telegram_clients` содержит долгоживущий `TelegramClientManager`. Он создаётся контейнером приложения и живёт ровно один lifespan конкретного экземпляра FastAPI. QR-сессии и их фоновые задачи вынесены в `QrAuthManager`.

```
ApplicationContainer
└── TelegramClientManager
    ├── QrAuthManager
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

Каждый HTTP-роут передаёт в `parse_filters` явный whitelist полей. Некорректный
формат, оператор, тип значения или запрещённое поле возвращают HTTP 422.

## Сортировка списков

`BaseRepository.get_list()` и `get_all()` применяют `order_by=-created_at` по
умолчанию. Формат `field` означает ASC, `-field` — DESC. Имя проверяется по ORM-модели,
а вторичная сортировка по `id` обеспечивает стабильную пагинацию.

## Фабрика приложения

`create_app()` — composition root. Она создаёт `ApplicationContainer`, регистрирует
обработчики на принадлежащем ему consumer и подменяет FastAPI-зависимости на
компоненты этого контейнера. Поэтому экземпляры приложения не делят шину или
Telegram-клиенты и могут тестироваться изолированно.

## Внутренние роуты (/internal/)

Роуты с префиксом `/internal/` — для межмодульного взаимодействия. Они не используют пользовательский JWT, но требуют сервисный ключ в заголовке `X-Internal-Service-Key`. Значение задаётся обязательной переменной `INTERNAL_SERVICE_KEY`; Docker network и k8s NetworkPolicy остаются дополнительными ограничениями.

## Межмодульное взаимодействие

Модули **не импортируют друг друга напрямую**. Для взаимодействия используются:

1. **Шина событий** — для асинхронной связи (fire-and-forget)
2. **Клиенты из `src/core/clients/`** — для синхронных вызовов в монолите
3. **HTTP к `/internal/`** — внешний контракт для будущего разделения сервисов

**Пример:** Если модулю `notifications` нужно получить файл из модуля `media`:

```python
# НЕПРАВИЛЬНО:
from src.modules.media.service import MediaService  # прямой импорт запрещён

# ПРАВИЛЬНО для текущего монолита:
from src.core.clients.media_client import MediaClient

file_data = await MediaClient().get_media_file(str(file_id))
```

**Пример для notifications модуля:** Резолв email по auth_id через internal API users:

```python
from src.core.clients.users_client import UsersClient

client = UsersClient()
email = await client.resolve_email_by_auth_id(auth_id)
```

URL внутреннего API вынесен в настройки: `settings.INTERNAL_API_BASE_URL = "http://localhost:8000/internal"`.

## Межмодульное взаимодействие через клиенты (src/core/clients/)

### Текущая реализация (Modular Monolith)

**Важно:** В текущей реализации клиенты используют **прямые импорты сервисов** модулей, а не HTTP-запросы. Это осознанное решение для монолитной архитектуры, которое будет изменено при выносе модулей в микросервисы.

Для устранения дублирования кода общие клиенты вынесены в модуль `src/core/clients/`:

| Клиент | Методы | Описание |
|--------|--------|----------|
| `UsersClient` | `resolve_email_by_auth_id(auth_id)` | Резолв email по auth_id через `UserService` |
| `AuthClient` | `resolve_auth_by_identifier(identifier)` | Получение auth по identifier через `AuthService` |

**Пример использования:**

```python
# В любом модуле:
from src.core.clients import UsersClient, AuthClient

users_client = UsersClient()
email = await users_client.resolve_email_by_auth_id(auth_id)

auth_client = AuthClient()
auth = await auth_client.resolve_auth_by_identifier(email)
```

**Преимущества текущего подхода:**
- Устранение дублирования кода
- Прямые вызовы без накладных расходов HTTP
- Упрощение тестирования (легко замокать)
- Сохранение типизации и IDE-автодополнения

**План миграции на микросервисы:**

При выносе модулей в отдельные сервисы клиенты будут переписаны на HTTP-запросы:

```python
# Будущая реализация (микросервисы):
class UsersClient:
    async def resolve_email_by_auth_id(self, auth_id: UUID) -> str | None:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.USERS_SERVICE_URL}/internal/users/",
                params={"filters": f"auth_id+eq+{auth_id}"}
            )
            data = response.json()
            return data[0].get("email") if data else None
```

### Архитектурное решение

**Почему сейчас используются импорты:**

1. **Монолитная архитектура** — все модули работают в одном процессе, нет сетевого взаимодействия
2. **Производительность** — прямые вызовы быстрее HTTP-запросов
3. **Типизация** — сохраняется статическая типизация и автодополнение
4. **Простота** — не нужно поднимать HTTP-сервер для внутренних вызовов

**Когда переходить на HTTP:**

- При выносе модуля `users` в отдельный микросервис
- При выносе модуля `auth` в отдельный микросервис
- При необходимости масштабирования модулей независимо

**Как определить готовность к миграции:**

- Модуль стабилен и не меняется часто
- Есть потребность масштабировать модуль независимо
- Команда готова поддерживать отдельный сервис

---

Модуль `media` спроектирован как независимый сервис — файлы не имеют владельца (`auth_id`), доступ контролируется через `is_public` (публичный доступ) или network-level (внутренний API).

## Шина сообщений

### Сборка producer/consumer (`src/bus/__init__.py`)

Один модуль создаёт согласованную пару для выбранного транспорта:

```python
from src.bus import get_consumer, get_producer

producer = get_producer()  # Только publish/start/stop
consumer = get_consumer()  # subscribe/get_subscribers/start/stop
```

**Зачем?**
- producer не знает об обработчиках
- consumer владеет подписками и диспетчеризацией
- in-memory пара использует общую очередь, Kafka-пара — общий брокер
- `main.py` и модульные зависимости получают одну и ту же пару

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
