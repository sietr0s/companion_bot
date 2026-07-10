# Modular Monolith Starter

Шаблон сервиса на основе **Modular Monolith** — изолированные модули в одном процессе, готовые к выносу в микросервисы.

## Быстрый старт

```bash
python3.12 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # укажите DATABASE_URL, JWT_SECRET_KEY, TG_API_ID, TG_API_HASH
uvicorn src.main:app --reload
```

Swagger UI: `http://localhost:8000/docs`

### Pre-commit hooks

Для автоматической проверки кода перед коммитом:

```bash
# Установка pre-commit
pip install pre-commit
pre-commit install

# Запуск всех проверок вручную
pre-commit run --all-files
```

**Что проверяется:**
- `ruff` — линтинг и форматирование
- `mypy` — проверка типов
- `pytest` — тесты (при push)
- Трейлинг-пробелы, концовка файлов, YAML-синтаксис

## Документация

| Документ | Описание |
|----------|----------|
| [Архитектура](docs/architecture.md) | Принципы, стек, структура проекта, ClientManager |
| [API](docs/api.md) | Все HTTP-эндпоинты: Auth, Users, Telegram Clients |
| [База данных](docs/database.md) | Модели, поля, индексы, ER-диаграмма |
| [Шина сообщений](docs/bus.md) | Топики, события, реализации, диаграмма потоков |
| [Новый модуль](docs/new-module.md) | Пошаговый гайд создания модуля (12 шагов + чеклист) |
| [Правила изоляции](docs/isolation-rules.md) | Что разрешено / запрещено, паттерны общения |
| [Развёртывание](docs/deployment.md) | Локальная разработка, Docker, Production, миграции |
| [Фильтрация](docs/filters.md) | Универсальная система фильтрации, операторы, примеры |

## Модули

| Модуль | Префикс | Описание |
|--------|---------|----------|
| **auth** | `/auth` | Регистрация, вход, JWT (role: user/admin) |
| **users** | `/users` | Профиль пользователя (CRUD) |
| **telegram_clients** | `/telegram-clients` | Telegram-аккаунты, авторизация, чаты, сообщения |
| **notifications** | `/notifications` | Шаблоны (Jinja2), отправка email, история (admin) |
| **media** | `/media` | Загрузка/скачивание файлов, StorageProvider Protocol, is_public доступ |
| **internal** | `/internal` | Межмодульный API: users, media (network-level) |
| **job_bot** | — | Telegram-бот (aiogram): шлюз для входящих/исходящих сообщений |
| **job_matcher** | — | Бизнес-логика подбора вакансий: парсинг, классификация, подписки |

## Тесты и линтинг

```bash
# Unit и интеграционные тесты
pytest tests/ -v

# E2E тесты (реальный Telegram API)
pytest tests/e2e/ -v

# Запуск с маркерами
pytest tests/e2e/ -v -m "e2e and telegram"

# Линтинг
ruff check src/ tests/
```

### E2E тесты

E2E тесты используют **реальный Telegram API** (Telethon + aiogram) для проверки сквозной интеграции модулей.

**Быстрый старт:**

```bash
# 1. Настройка окружения
cp .env.test.example .env.test
# Заполните TG_API_ID, TG_API_HASH, TG_BOT_TOKEN, TG_TEST_USER_PHONE

# 2. Первая аутентификация (создание session)
mkdir -p /tmp/ms_starter_e2e_tests
pytest tests/e2e/scenarios/test_registration.py -v

# 3. Запуск всех E2E тестов
pytest tests/e2e/ -v
```

**Документация:** См. [docs/e2e-testing.md](docs/e2e-testing.md) для подробного руководства.

**Структура тестов:**
- `tests/e2e/scenarios/` — User Journey (регистрация, сообщения, команды боту, match)
- `tests/e2e/conftest.py` — фикстуры (Telethon клиент, aiogram бот, БД, шина)
- `tests/e2e/utils.py` — вспомогательные функции

**Маркеры:**
- `@pytest.mark.e2e` — E2E тесты
- `@pytest.mark.telegram` — тесты с Telegram API
- `@pytest.mark.bot` — тесты с ботом
- `@pytest.mark.slow` — медленные тесты (полный цикл)
