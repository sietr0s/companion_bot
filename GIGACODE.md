# GigaCode Context: ms_starter (Modular Monolith)

## Project Overview

**ms_starter** — это шаблон сервиса на основе архитектуры **Modular Monolith** (модульный монолит). Приложение состоит из изолированных бизнес-модулей, работающих в одном процессе, каждый из которых спроектирован для будущего выноса в отдельный микросервис **без переписывания бизнес-логики**.

### Основные принципы
- **Изоляция модулей** — модули не импортируют друг друга напрямую
- **Связь через шину** — взаимодействие только через события (MessageBus)
- **Интерфейсы (Protocol)** — зависимости между модулями через абстракции
- **Нет ForeignKey между модулями** — каждая таблица принадлежит одному модулю
- **DI-контейнер** — FastAPI Depends для внедрения зависимостей
- **Единый реестр топиков** — все топики определены в `BusTopics`

### Технологический стек
- **Язык**: Python 3.11+
- **Фреймворк**: FastAPI
- **БД**: PostgreSQL + asyncpg
- **ORM**: SQLAlchemy 2.0 (async)
- **Миграции**: Alembic
- **Валидация**: Pydantic v2
- **Аутентификация**: JWT (PyJWT), bcrypt
- **Шина сообщений**: aiokafka / in-memory (переключаемая)
- **Telegram API**: Telethon
- **Шаблоны**: Jinja2

### Структура проекта
```
src/
├── base/                        # Базовые абстракции (model, repository, service)
├── core/                        # Ядро (config, database, security, exceptions, clients)
├── bus/                         # Шина сообщений (interface, in_memory, kafka, providers)
└── modules/                     # Бизнес-модули
    ├── auth/                    # Регистрация, вход, JWT
    │   └── dependencies.py      # DI-зависимости модуля
    ├── users/                   # Профили пользователей
    │   └── dependencies.py      # DI-зависимости модуля
    ├── telegram_clients/        # Telegram-аккаунты, сообщения
    │   └── dependencies.py      # DI-зависимости модуля
    ├── notifications/           # Шаблоны, отправка email
    │   └── dependencies.py      # DI-зависимости модуля
    ├── media/                   # Загрузка/скачивание файлов
    │   └── dependencies.py      # DI-зависимости модуля
    ├── job_bot/                 # Telegram-бот (aiogram): шлюз сообщений
    │   ├── bot.py               # Создание Bot/Dispatcher
    │   ├── service.py           # Отправка сообщений через бота
    │   └── handlers.py          # Подписка на шину (входящие/исходящие)
    ├── classifier/              # AI-классификация текстов (категории, NER)
    │   ├── ai/                  # Абстракции и реализации AI-классификаторов
    │   ├── models.py            # Category, ClassificationLog
    │   ├── repository.py        # Репозиторий категорий и логов
    │   ├── service.py           # ClassifierService
    │   └── handlers.py          # Обработчики шины
    └── job_matcher/             # Бизнес-логика подбора вакансий
        ├── models.py            # Subscription, JobOffer
        ├── repository.py        # Репозиторий подписок
        ├── service.py           # JobMatcherService
        └── handlers.py          # Обработчики шины
```

## Building and Running

### Локальный запуск
```bash
# Создание виртуального окружения
python3.12 -m venv venv && source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Настройка окружения
cp .env.example .env
# Отредактируйте .env: DATABASE_URL, JWT_SECRET_KEY, TG_API_ID, TG_API_HASH

# Запуск сервера
uvicorn src.main:app --reload

# Swagger UI: http://localhost:8000/docs
```

### Docker Compose
```bash
# Базовый запуск (только app + PostgreSQL)
docker-compose up -d

# С Kafka
docker-compose --profile kafka up -d

# С pgAdmin
docker-compose --profile admin up -d
```

### Тестирование и линтинг
```bash
# Запуск тестов
pytest tests/ -v

# Линтинг
ruff check src/ tests/

# Форматирование (если настроено)
ruff format src/ tests/
```

## Development Conventions

### Обработка ошибок
- **Сервисы выбрасывают исключения** (`NotFoundError`, `ConflictError`, `UnauthorizedError`)
- **Глобальный handler** в `main.py` перехватывает `AppException` и возвращает JSON с правильным статусом
- **Нет локальных try/except** в роутерах и обработчиках шины — исключения пробрасываются наверх

**Пример:**
```python
# ✅ Правильно: сервис кидает исключение
async def get_profile(self, session, auth_id):
    profile = await self.repository.get_by_auth_id(session, auth_id)
    if not profile:
        raise NotFoundError(detail="Профиль не найден")
    return profile

# ❌ Неправильно: возвращать None
async def get_profile(self, session, auth_id):
    profile = await self.repository.get_by_auth_id(session, auth_id)
    if not profile:
        return None  # ❌
    return profile
```

### Логирование
- Используйте `%`-форматирование: `logger.info("Сообщение: %s", value)`
- Уровни: `info` (нормальные события), `warning` (предупреждения), `exception` (в блоках `except`)
- **Никаких `print()`** — только `logger`

### Типизация
- Полная типизация с Python 3.10+ синтаксисом (`str | None`, не `Optional[str]`)
- `Protocol` для интерфейсов между модулями
- Generics через `TypeVar` для репозиториев

### Именование
| Элемент | Стиль | Пример |
|---------|-------|--------|
| Переменные, функции | `snake_case` | `auth_id`, `get_profile()` |
| Классы | `PascalCase` | `UserService`, `TelegramClientManager` |
| Константы | `UPPER_SNAKE_CASE` | `ERROR_MESSAGES` |
| Топики шины | `dot.notation` | `user.registered`, `tg.message.send` |

### Межмодульное взаимодействие

#### Через шину (асинхронно)
```python
# Публикация события (в сервисе)
await self.message_bus.publish(
    BusTopics.USER_REGISTERED,
    UserRegistered(auth_id=account.id, email=data.email).to_bus_dict(),
)

# Подписка (в handlers.py)
@bus.subscribe(BusTopics.USER_REGISTERED)
async def handle_user_registered(message: dict):
    logger.info("Новый пользователь: auth_id=%s", message.get("auth_id"))
```

#### Через клиенты (синхронно, прямой вызов)
```python
# Новый подход: клиенты используют DI для получения сервисов
from src.core.clients import UsersClient

client = UsersClient()
email = await client.resolve_email_by_auth_id(auth_id)  # Прямой вызов, без HTTP
```

**Старый подход (HTTP)** — всё ещё поддерживается для совместимости, но новый код должен использовать прямые вызовы через клиентов.

### Работа с БД
- **SQLAlchemy 2.0 async** с `Mapped` аннотациями
- **Сессии** через `Depends(get_session)` в роутерах
- **Клиенты** сами управляют сессией через `async for session in get_session()`

### Тестирование
- **SQLite in-memory** для быстрых тестов (не требует PostgreSQL)
- **Фикстуры** в `tests/conftest.py`: `db_session`, `message_bus`, `auth_service`, `client`
- **Асинхронный HTTP-клиент** (`httpx.AsyncClient` с `ASGITransport`) для интеграционных тестов
- **Автоматический откат** транзакций после каждого теста

**Пример теста:**
```python
async def test_get_profile_not_found(db_session: AsyncSession):
    service = UserService(repository=UserRepository(), message_bus=InMemoryProducer())
    with pytest.raises(NotFoundError):
        await service.get_profile(db_session, uuid.uuid4())
```

## Key Files

| Файл | Описание |
|------|----------|
| `src/main.py` | Точка входа, инициализация шины, регистрация роутеров и обработчиков |
| `src/core/exceptions.py` | Иерархия исключений (`AppException`, `NotFoundError`, `ConflictError`, `UnauthorizedError`) |
| `src/core/clients/` | Клиенты для межмодульного взаимодействия (`UsersClient`, `MediaClient`) |
| `src/bus/interface.py` | Protocol `MessageBus` — интерфейс шины |
| `tests/conftest.py` | Общие фикстуры для тестов |
| `STYLEGUIDE.md` | Подробный гайд по стилю кода в проекте |
| `docs/architecture.md` | Детальная документация по архитектуре |

## Creating a New Module

Следуйте гайду в `docs/new-module.md` (12 шагов + чеклист). Кратко:

1. Создать директорию `src/modules/<module_name>/`
2. Создать `models.py` — SQLAlchemy модели
3. Создать `schemas/api.py` — Pydantic схемы для API
4. Создать `schemas/events.py` — схемы событий шины
5. Создать `repository.py` — репозиторий с кастомными методами
6. Создать `service.py` — бизнес-логика
7. Создать `router.py` — HTTP роуты (публичные)
8. Создать `internal.py` — HTTP роуты (внутренние, если нужно)
9. Создать `handlers.py` — обработчики событий шины
10. **Создать `dependencies.py`** — DI-фабрики модуля (не в `core/dependencies.py`)
11. Зарегистрировать топики в `src/core/bus_topics.py`
12. Подключить роутер в `src/main.py`
13. Зарегистрировать обработчики шины в `src/main.py`

## Important Notes

- **TelegramClientManager** — singleton, управляется в `main.py`, не через DI
- **Session-файлы Telegram** хранятся в `sessions/` (маунтится в Docker)
- **Клиенты** получают session внутри методов через `get_session()` — не нужно передавать вручную
- **Обработчики шины** не используют try/except — ошибки пробрасываются наверх
- **Миграции** через Alembic: `alembic revision --autogenerate -m "description"`

## Documentation Links

- `STYLEGUIDE.md` — стиль кода, паттерны, примеры
- `docs/architecture.md` — архитектура проекта
- `docs/api.md` — все HTTP-эндпоинты
- `docs/database.md` — модели БД, ER-диаграмма
- `docs/bus.md` — шина сообщений, топики, события
- `docs/new-module.md` — создание нового модуля
- `docs/deployment.md` — развёртывание (Docker, Kafka)
