# Обзор проекта `micromonolit`

Этот файл — карта проекта для обсуждения в чате. Он описывает состояние репозитория по исходникам и конфигурации на 19.07.2026. Это не замена специализированной документации в `docs/`, а единая точка входа: что делает система, из каких частей состоит, как проходит запрос или событие и где искать код.

## 1. Коротко: зачем нужен проект

Проект — асинхронный Python-сервис в стиле **modular monolith**. Инфраструктурно это заготовка для модульного приложения, которое можно запускать одним процессом, а бизнес-сценарий уже ориентирован на агрегирование и подбор вакансий:

- пользователь регистрируется и входит через JWT;
- пользователь подключает Telegram-аккаунты и задаёт правила чтения чатов;
- сообщения из Telegram принимаются, сохраняются и передаются в бизнес-контур;
- текст вакансии парсится и классифицируется AI-модулем;
- вакансии сопоставляются с подписками пользователя;
- подходящие предложения отправляются пользователю через Telegram-бота и/или email;
- администратор управляет пользователями, Telegram-аккаунтами, категориями, шаблонами уведомлений и вакансиями через React-панель.

Главная архитектурная идея: модули находятся в одном процессе и используют общую БД, но взаимодействуют через явно определённые контракты — события/команды шины и узкие HTTP-клиенты. Поэтому отдельный модуль потенциально можно вынести в микросервис без переписывания его бизнес-сервиса.

## 2. Технологический стек

### Backend

- Python 3.11+;
- FastAPI + Uvicorn;
- Pydantic v2 и `pydantic-settings` для схем и конфигурации;
- SQLAlchemy 2.0 в async-режиме + `asyncpg`;
- PostgreSQL 15 в Docker Compose;
- Alembic для миграций;
- JWT (`PyJWT`) и `bcrypt`;
- `httpx` для межмодульных HTTP-клиентов;
- собственная шина сообщений с двумя реализациями: in-memory и Kafka (`aiokafka`);
- Telethon для пользовательских Telegram-аккаунтов;
- aiogram для Telegram-бота;
- Jinja2 для шаблонов уведомлений;
- Hugging Face/`gliclass`/PyTorch для zero-shot классификации.

### Frontend

- React 18 + TypeScript;
- Vite;
- React Router;
- TanStack React Query;
- Ant Design;
- API-клиент генерируется из `frontend/openapi.json`.

### Проверки и доставка

- `pytest`, включая unit/integration и отдельные E2E-сценарии;
- Ruff, mypy и pre-commit;
- Dockerfile для backend и frontend;
- Docker Compose с app, frontend, PostgreSQL и опциональными Kafka/Zookeeper/pgAdmin.

## 3. Структура репозитория

```text
.
├── src/
│   ├── main.py                 # composition root, создание FastAPI и lifespan
│   ├── base/                   # общие ORM/Repository/Service/filters/schemas
│   ├── core/                   # конфигурация, БД, security, DI, seed, HTTP-клиенты
│   ├── bus/                    # интерфейс шины, in-memory, Kafka, DLQ/error handling
│   └── modules/                # изолированные предметные модули
├── frontend/                   # административная React-панель
├── templates/                  # email и Telegram Jinja-шаблоны
├── alembic/                    # миграции схемы БД
├── tests/                      # unit, integration, bus и E2E тесты
├── docs/                       # архитектура, API, БД, шина и документация модулей
├── scripts/                    # служебные скрипты, в том числе генерация OpenAPI-клиента
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

## 4. Архитектура backend

### Слои внутри модуля

Типичный модуль разделён на следующие роли:

```text
router / handler
        ↓
service                 ← бизнес-правила и orchestration
        ↓
repository              ← SQLAlchemy-запросы и persistence
        ↓
model                   ← ORM-модель

schemas                 ← HTTP/event DTO и валидация
dependencies            ← FastAPI DI-фабрики
constants               ← enum, topic names, сообщения ошибок
```

HTTP-роутер отвечает за транспорт: авторизацию, параметры и преобразование ответа. Сервис принимает решения предметной области. Репозиторий изолирует доступ к БД. Обработчики шины — адаптеры асинхронных входящих сообщений; они создают сессию/зависимости и вызывают сервисы.

Общие примитивы находятся в `src/base/`: `BaseModel` добавляет UUID и timestamps, `BaseRepository` даёт CRUD, пагинацию, фильтры и сортировку, `BaseService` задаёт типовой сервисный слой. Конкретные модули расширяют этот каркас своими запросами и правилами.

### Composition root и жизненный цикл

Точка сборки — `src/main.py`:

1. создаётся `ApplicationContainer` (`src/core/container.py`);
2. выбирается реализация шины через `MESSAGE_BUS`;
3. регистрируются обработчики всех модулей;
4. подключаются public и internal routers;
5. в lifespan инициализируются БД, seed администратора, категории классификатора, AI-модель, локальное хранилище и Telegram-сессии;
6. запускается Telegram-бот в polling или webhook-режиме;
7. при остановке корректно закрываются bot, Telegram clients, consumer и producer.

Это хорошая точка для dependency overrides в тестах: `create_app(container)` позволяет собрать приложение с тестовым контейнером.

### Модули и ответственность

| Модуль | Роль | Основные сущности/интерфейсы |
|---|---|---|
| `auth` | регистрация, вход, смена/удаление аккаунта, JWT, роли user/admin | `Auth`, `AuthService`, `AuthRepository` |
| `users` | профиль пользователя и Telegram-профиль | `User`, `Telegram`, `UserService` |
| `telegram_clients` | пользовательские Telegram-аккаунты, SMS/2FA/QR-авторизация, чаты, сообщения, фильтры чтения | `TelegramAccount`, `TelegramSettings`, `TelegramChatState`, `TelegramClientManager` |
| `job_bot` | транспортный шлюз Telegram-бота: входящие команды и исходящие сообщения | aiogram `Bot`/`Dispatcher`, `BotService` |
| `job_matcher` | предметная логика вакансий: парсинг, сохранение, подписки, сопоставление | `JobOffer`, `Subscription`, сервисы matcher-а |
| `classifier` | категории, NER и классификация текста | `Category`, `ClassificationLog`, `ZeroShotCategoryClassifier`, `RegexEntityExtractor` |
| `notifications` | шаблоны, рендеринг, SMTP и история отправок | `NotificationTemplate`, `NotificationLog`, `SmtpProvider` |
| `media` | загрузка, скачивание и удаление файлов | `StoredFile`, `StorageProvider`, `LocalStorage` |

## 5. Основные сквозные потоки

### Регистрация

```text
POST /api/v1/public/auth/register
  → auth.AuthService
  → Auth + событие auth.event.user.registered
  → users handler
  → создание User-профиля
```

### Обработка вакансии из Telegram

```text
Telegram/Telethon
  → telegram_clients: message.received
  → job_matcher: parse и сохранить JobOffer
  → classifier: command.classify
  → classifier.event.classify.completed
  → job_matcher: обновить категории и найти подходящие Subscription
  → notifications.command.send и/или job_bot.command.send_message
  → email/Telegram пользователю
```

### Telegram-бот

```text
aiogram incoming handler
  → job_bot.event.message.incoming
  → job_matcher / users subscribers

job_matcher / другой модуль
  → job_bot.command.send_message
  → aiogram BotService
  → Telegram user
```

### Межмодульный HTTP-вызов

В проекте предусмотрены `src/core/clients/*`: базовый async HTTP-клиент и клиенты auth/users/media/classifier. Это контрактный слой для вызовов `/internal`, который особенно важен при последующем выносе модуля в отдельный процесс.

## 6. Шина сообщений

Шина абстрагирована интерфейсами из `src/bus/interface.py`. В dev/test используется in-memory транспорт, в deployment можно выбрать Kafka. Для ошибок предусмотрены safe handling и DLQ `bus.dlq`.

Нейминг топиков разделяет владельца и намерение:

- события: `auth.event.*`, `users.event.*`, `telegram_clients.event.*`, `job_matcher.event.*`, `classifier.event.*`;
- команды: `telegram_clients.command.*`, `notifications.command.*`, `classifier.command.*`, `job_bot.command.*`.

Полный реестр находится в `src/core/bus_topics.py`, а подробности — в [docs/bus.md](docs/bus.md). Важное правило: модуль публикует собственные события и отправляет команды владельцам чужих side effects; прямой импорт внутреннего сервиса другого модуля считается нарушением изоляции.

## 7. Данные и persistence

- единый SQLAlchemy `Base` позволяет Alembic видеть все ORM-модели;
- primary key — UUID;
- общие `created_at`/`updated_at` задаются в `BaseModel`;
- async session создаётся через `src/core/database.py`;
- миграции находятся в `alembic/versions/`;
- универсальные фильтры поддерживают операции вроде `eq`, `contains`, диапазоны и сортировку с `-field` для descending;
- файлы хранятся отдельно от метаданных БД через `StorageProvider`; текущая реализация — local storage, интерфейс допускает S3.

Подробная карта таблиц и связей: [docs/database.md](docs/database.md).

## 8. API и frontend

FastAPI публикует health endpoint `/health`, public API модулей и internal API под `/internal`. OpenAPI доступен на `/docs`; frontend-клиент генерируется из зафиксированного `frontend/openapi.json`.

Текущие UI-разделы: dashboard, users, media, Telegram accounts/chats/settings, categories, notification templates/history и job offers. Защищённые маршруты проходят через `AuthContext` и `ProtectedRoute`, запросы к API организованы через generated client и React Query.

API-детали и фактические prefix-ы нужно сверять с [docs/api.md](docs/api.md) и роутерами в `src/modules/*/routers/`; тест `tests/test_router_prefixes.py` фиксирует ожидаемые префиксы.

## 9. Code style и инженерные правила

### Python

- форматирование Ruff: double quotes, 4 пробела, line length 100;
- Ruff lint: `E`, `W`, `F`, `I`, `B`, `C4`, `UP`, `N`, `SIM`, `TCH`;
- строгая типизация mypy (`strict = true`), явные типы у функций;
- async/await для I/O;
- Pydantic-схемы на границах HTTP и событий;
- зависимости передаются через DI/фабрики, а не создаются случайно внутри роутеров;
- бизнес-ошибки — через `AppException` и наследников (`NotFoundError`, `ConflictError`, `UnauthorizedError`, `InvalidFilterError`);
- тестовый код допускает `assert`, но production-код не должен обходить правила изоляции.

### Архитектурные правила

Разрешены импорты из `base`, `core`, `bus` и собственного модуля. Для общения с другим модулем используются шина, публичный контракт или HTTP-клиент. Нельзя напрямую импортировать модели/репозитории/сервисы чужого модуля и нельзя ходить из одного модуля в чужую таблицу напрямую.

### Frontend

TypeScript/React-код форматируется Prettier, проверяется ESLint, API-типы генерируются, а не поддерживаются вручную. Роутинг централизован в `frontend/src/router.tsx`, общие контексты находятся в `frontend/src/contexts`.

Полные правила: [STYLEGUIDE.md](STYLEGUIDE.md) и [docs/isolation-rules.md](docs/isolation-rules.md).

## 10. Тестирование

```bash
# backend unit + integration
pytest tests/ -v

# быстрые проверки
ruff check src/ tests/
mypy src/

# frontend
cd frontend
npm run lint
npm run build
```

Тестовые уровни:

- `tests/base`, `tests/core` — базовые компоненты, security, config, clients;
- `tests/bus` — in-memory bus, Kafka consumer и DLQ;
- `tests/modules/*` — сервисы, репозитории, handlers и HTTP integration;
- `tests/modules/integration` — связи job matcher/classifier;
- `tests/e2e` — сценарии с реальными Telegram API/Telethon/aiogram и внешними настройками.

В тестах production transport обычно заменяется на in-memory producer, БД — на SQLite/тестовую сессию, а зависимости — fixtures/overrides.

## 11. Запуск и окружения

Локальный backend описан в [README.md](README.md). Docker-сценарий — в [DOCKER.md](DOCKER.md) и `docker-compose.yml`.

Минимально нужны секреты и настройки из `.env.example`: `DATABASE_URL`, `JWT_SECRET_KEY`, Telegram API credentials; для соответствующих функций — bot token, SMTP и параметры классификатора. Секреты из `.env` нельзя переносить в документацию, коммиты или логи.

В Compose:

- приложение: `http://localhost:8000`;
- Swagger: `http://localhost:8000/docs`;
- frontend: `http://localhost:3000`;
- Kafka включается профилем `kafka`;
- pgAdmin — профилем `admin`.

Перед production необходимо заменить dev secrets/default passwords, ограничить debug/admin endpoints, настроить безопасное хранение Telegram sessions, persistence media/Hugging Face cache и отдельный процесс/worker для тяжёлой AI-инициализации, если это потребуется по нагрузке.

## 12. Что особенно важно понимать при обсуждении

1. **Это не классический микросервисный deployment.** Код разделён по bounded-context-подобным модулям, но сейчас они живут в одном приложении и общей БД.
2. **`job_bot` и `telegram_clients` — разные Telegram-роли.** Первый работает как бот приложения, второй управляет пользовательскими Telegram-сессиями через Telethon.
3. **События и команды не равны друг другу.** `*.event.*` сообщает о факте, `*.command.*` просит владельца другого модуля выполнить действие.
4. **AI-классификатор загружается при старте.** Это влияет на время запуска, память и требования к cache/CPU/GPU.
5. **Межмодульная изоляция — архитектурный контракт, а не только соглашение по каталогам.** Её нужно поддерживать импортами, DTO и тестами.
6. **Текущее состояние ветки нельзя считать чистой baseline-версией.** В рабочем дереве есть многочисленные изменённые и новые файлы; при разборе конкретного поведения важно отличать уже существующую архитектуру от незакоммиченных изменений.

## 13. Полезный маршрут чтения кода

1. `src/main.py` — как приложение собирается и стартует.
2. `src/core/container.py`, `src/core/config.py`, `src/core/database.py` — зависимости, настройки и БД.
3. `src/bus/interface.py`, `src/bus/in_memory/*`, `src/bus/kafka/*`, `src/core/bus_topics.py` — транспорт событий.
4. `src/base/model.py`, `src/base/repository.py`, `src/base/service.py` — общий persistence/service framework.
5. `src/modules/job_matcher/` — центральный бизнес-сценарий вакансий.
6. `src/modules/telegram_clients/` и `src/modules/job_bot/` — два Telegram-контура.
7. `src/modules/classifier/` и `src/modules/notifications/` — классификация и доставка результата.
8. `frontend/src/router.tsx` и `frontend/src/pages/` — административный интерфейс.
9. `tests/modules/integration/` и `tests/e2e/scenarios/` — сквозные сценарии.

## 14. Вопросы, которые стоит разобрать следующими

- Какие модули считаются окончательными bounded contexts, а какие пока технические границы?
- Должны ли `job_matcher`, `classifier` и `notifications` оставаться в одном процессе при production-нагрузке?
- Как гарантируются idempotency, retries и ordering для Kafka-событий?
- Где проходит граница между synchronous internal HTTP и event-driven взаимодействием?
- Как защищаются Telegram session-файлы и персональные сообщения?
- Как измеряются latency/throughput классификатора и что происходит при недоступности модели?
- Нужны ли outbox/inbox-паттерны, трассировка событий и полноценный health/readiness check?
- Какие ограничения и правила должны быть добавлены в CI до начала активного выделения сервисов?

## Связанные документы

- [Архитектура](docs/architecture.md)
- [API](docs/api.md)
- [Шина сообщений](docs/bus.md)
- [База данных](docs/database.md)
- [Развёртывание](docs/deployment.md)
- [Документация модулей](docs/modules/README.md)
- [Создание нового модуля](docs/new-module.md)
- [E2E-тестирование](docs/e2e-testing.md)
