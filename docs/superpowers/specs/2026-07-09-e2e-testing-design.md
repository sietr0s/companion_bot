# Дизайн-документ: E2E тестирование ms_starter

**Дата:** 2026-07-09
**Статус:** Approved
**Автор:** GigaCode

---

## 1. Overview

### 1.1. Цель

Спроектировать и реализовать систему E2E тестов для проекта ms_starter (Modular Monolith) с использованием **реального Telegram API** для тестирования интеграции между модулями.

### 1.2. Проблема

Текущая тестовая инфраструктура покрывает unit и интеграционные тесты с моками, но не тестирует:
- Реальную интеграцию с Telegram API (Telethon)
- Взаимодействие бота (aiogram) с реальными пользователями
- Сквозные пользовательские сценарии через несколько модулей

### 1.3. Решение

E2E тесты с реальным Telegram:
- **Бот тестируется через Telethon User API** — тестовый пользователь отправляет сообщения боту
- **telegram_clients тестируется через тестового бота** — бот шлёт сообщения, система обрабатывает

---

## 2. Архитектура тестов

### 2.1. Схема взаимодействия

```
┌─────────────────────────────────────────────────────────────────┐
│                        E2E ТЕСТЫ                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐         ┌──────────────┐                     │
│  │  Telethon    │         │   aiogram    │                     │
│  │  (User API)  │         │     (Bot)    │                     │
│  └──────┬───────┘         └──────┬───────┘                     │
│         │                        │                              │
│         │  1. Пишет боту         │                              │
│         │───────────────────────>│                              │
│         │                        │                              │
│         │                        │  2. bot.message.incoming     │
│         │                        │─────────────────────┐        │
│         │                        │                     │        │
│         │                        │  3. job_matcher     │        │
│         │                        │<────────────────────┘        │
│         │                        │                              │
│         │                        │  4. bot.message.outgoing     │
│         │                        │<────────────────────┐        │
│         │  5. Ответ бота         │                     │        │
│         │<───────────────────────│                     │        │
│         │                        │                      │       │
│  ┌──────┴───────┐         ┌──────┴───────┐                     │
│  │  Telegram    │         │  telegram_   │                     │
│  │   Account    │         │   clients    │                     │
│  └──────┬───────┘         └──────┬───────┘                     │
│         │                        │                              │
│         │  6. Бот шлёт сообщение │                              │
│         │<───────────────────────│                              │
│         │                        │                              │
│         │  7. tg.message.received│                              │
│         │───────────────────────>│                              │
│         │                        │                              │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2. Компоненты

| Компонент | Описание | Режим |
|-----------|----------|-------|
| **Telethon Client** | Telegram User API для отправки сообщений боту | Реальный API |
| **aiogram Bot** | Бот для получения/отправки сообщений | Polling |
| **TelegramClientManager** | Singleton для управления TG-аккаунтами | Реальный API |
| **MessageBus** | In-memory шина для событий | InMemoryProducer |
| **PostgreSQL** | База данных для тестов | Реальная БД |
| **FastAPI TestClient** | HTTP-клиент для API вызовов | httpx AsyncClient |

### 2.3. Структура тестов

```
tests/e2e/
├── scenarios/                    # User Journey (MVP: 5 тестов)
│   ├── test_registration.py      # Регистрация + подключение TG
│   ├── test_incoming_message.py  # Входящее сообщение от бота
│   ├── test_outgoing_message.py  # Исходящее сообщение через TG
│   ├── test_bot_command.py       # Команда боту (/start)
│   └── test_full_match_cycle.py  # Полный цикл match
├── components/                   # Будущее расширение
│   ├── test_telegram_clients.py
│   └── test_job_bot.py
├── conftest.py                   # E2E фикстуры
└── sessions/                     # Session-файлы (.gitignore)
    └── test_e2e.session
```

---

## 3. Стратегия тестирования

### 3.1. Режим тестирования

| Аспект | Решение | Обоснование |
|--------|---------|-------------|
| **Telegram API** | Реальный (production-like) | Тестирует реальную интеграцию |
| **Аккаунты** | 1 тестовый аккаунт | Достаточно для MVP, проще настройка |
| **Чаты** | Только личные сообщения (ЛС) | Упрощает тесты, покрывает 80% сценариев |
| **Изоляция** | Быстрая (1 session на все тесты) | Баланс скорости и чистоты |
| **БД** | PostgreSQL с автооткатом | Как в production, изоляция тестов |
| **Session-файлы** | `/tmp/ms_starter_e2e_tests/` | Очищается между запусками CI |
| **Credentials** | `.env.test` (в `.gitignore`) | Безопасность, удобство |

### 3.2. Изоляция тестов

```
┌─────────────────────────────────────────────────────────┐
│                  Уровень изоляции                       │
├─────────────────────────────────────────────────────────┤
│  Session-файль Telegram: 1 на все тесты (класс)         │
│  Telegram Bot:          1 на все тесты (модуль)         │
│  База данных:           Новая сессия на тест (откат)    │
│  Шина сообщений:        Новый InMemoryProducer на тест  │
│  HTTP-клиент:           Новый на тест (ASGITransport)   │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Настройка окружения

### 4.1. Переменные окружения (.env.test)

```bash
# Telegram API (Telethon)
TG_API_ID=123456
TG_API_HASH=abc123def456...
TG_TEST_USER_PHONE=+79991234567
TG_TEST_SESSION_PATH=/tmp/ms_starter_e2e_tests/test_e2e.session

# Telegram Bot (aiogram)
TG_BOT_TOKEN=bot123456:ABCdefGHIjklMNOpqrsTUVwxyz

# База данных
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ms_starter_e2e

# Шина сообщений
MESSAGE_BUS=in_memory

# Приложение
APP_ENV=test
```

### 4.2. Получение credentials

**TG_API_ID и TG_API_HASH:**
1. Зайти на https://my.telegram.org
2. Авторизоваться по номеру телефона
3. Перейти в "API development tools"
4. Создать новое приложение
5. Скопировать `App api_id` и `App api_hash`

**TG_BOT_TOKEN:**
1. Открыть @BotFather в Telegram
2. Отправить `/newbot`
3. Следовать инструкциям (имя, username)
4. Скопировать токен

**TG_TEST_USER_PHONE:**
- Использовать существующий тестовый аккаунт
- Или создать новый (требуется SIM-карта)

### 4.3. Первая аутентификация

Первый запуск тестов создаст session-файл:
```bash
# Первый запуск (интерактивный)
pytest tests/e2e/ -v --create-session

# В процессе:
# 1. Ввести номер телефона
# 2. Ввести код из SMS
# 3. Ввести 2FA пароль (если есть)
# 4. Session сохранится в TG_TEST_SESSION_PATH
```

---

## 5. Запуск тестов

### 5.1. Базовые команды

```bash
# Запуск всех E2E тестов
pytest tests/e2e/ -v --env-file=.env.test

# Запуск конкретного теста
pytest tests/e2e/scenarios/test_registration.py -v

# Запуск с логированием Telethon
pytest tests/e2e/ -v --log-cli-level=DEBUG

# Запуск без очистки БД (для отладки)
pytest tests/e2e/ -v --no-db-cleanup
```

### 5.2. CI/CD интеграция

```yaml
# .github/workflows/e2e-tests.yml
name: E2E Tests

on:
  push:
    branches: [master, release/*]
  workflow_dispatch:

jobs:
  e2e:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: ms_starter_e2e
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run E2E tests
        env:
          TG_API_ID: ${{ secrets.TG_API_ID }}
          TG_API_HASH: ${{ secrets.TG_API_HASH }}
          TG_TEST_USER_PHONE: ${{ secrets.TG_TEST_USER_PHONE }}
          TG_BOT_TOKEN: ${{ secrets.TG_BOT_TOKEN }}
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/ms_starter_e2e
        run: pytest tests/e2e/ -v
```

---

## 6. MVP тесты (5 сценариев)

### Тест 1: Регистрация и подключение Telegram

**Файл:** `test_registration.py`

**Сценарий:**
1. POST `/public/auth/register` → создание пользователя
2. POST `/public/telegram/auth/phone` → отправка номера
3. POST `/public/telegram/auth/code` → ввод SMS-кода
4. Проверка: аккаунт в БД, status="connected"

**Ожидаемый результат:**
- User создан в БД
- TelegramAccount создан, status="connected"
- Session-файл существует

**Edge cases:**
- 2FA required (требует пароль)
- Неверный код (ошибка)

---

### Тест 2: Входящее сообщение от бота

**Файл:** `test_incoming_message.py`

**Сценарий:**
1. Telethon: бот отправляет сообщение тестовому аккаунту
2. Система: `tg.message.received` публикуется в шину
3. Проверка: событие в шине, данные корректны

**Ожидаемый результат:**
- Событие `tg.message.received` в шине
- message_id, chat_id, text корректны

---

### Тест 3: Исходящее сообщение через Telegram

**Файл:** `test_outgoing_message.py`

**Сценарий:**
1. Публикация `tg.message.send` в шину
2. TelegramClientManager отправляет сообщение
3. Telethon проверяет получение

**Ожидаемый результат:**
- Сообщение доставлено
- message_id корректен

---

### Тест 4: Команда боту (/start)

**Файл:** `test_bot_command.py`

**Сценарий:**
1. Telethon: пользователь отправляет `/start` боту
2. Бот: `bot.message.incoming` в шину
3. job_matcher обрабатывает
4. Бот отвечает пользователю
5. Telethon проверяет ответ

**Ожидаемый результат:**
- `bot.message.incoming` в шине
- Бот отправил ответ
- `bot.message.outgoing` в шине

---

### Тест 5: Полный цикл match

**Файл:** `test_full_match_cycle.py`

**Сценарий:**
1. Telethon: сообщение боту ("ищу вакансию")
2. job_matcher: классификация → подбор
3. Бот: ответ с вакансиями
4. Telethon: проверка ответа

**Ожидаемый результат:**
- Сообщение классифицировано
- Вакансии подобраны
- Ответ отправлен пользователю

---

## 7. Фикстуры (conftest.py)

### 7.1. Ключевые фикстуры

```python
@pytest.fixture(scope="session")
async def e2e_db_session():
    """PostgreSQL сессия с автооткатом после каждого теста."""
    pass

@pytest.fixture(scope="session")
async def telegram_account():
    """Telethon клиент (1 session на все тесты)."""
    pass

@pytest.fixture(scope="session")
async def test_bot():
    """aiogram Bot (1 на все тесты)."""
    pass

@pytest.fixture
async def message_bus_collector():
    """Сборщик событий шины для проверки."""
    pass

@pytest.fixture
async def e2e_client():
    """httpx AsyncClient для API вызовов."""
    pass

@pytest.fixture
async def auth_token():
    """JWT токен тестового пользователя."""
    pass
```

### 7.2. Вспомогательные утилиты

```python
# tests/e2e/utils.py

async def wait_for_event(bus_collector, topic, timeout=5.0):
    """Ждать события из шины с таймаутом."""
    pass

async def assert_bot_response(telethon_client, bot_username, expected_text=None):
    """Проверить ответ от бота через Telethon."""
    pass
```

---

## 8. Backlog будущих расширений

### 8.1. Telegram-сценарии

| Приоритет | Тест | Описание |
|-----------|------|----------|
| P1 | 2FA аутентификация | Тест flow с паролем |
| P1 | Загрузка медиа | Проверка вложений из сообщений |
| P2 | Настройки чтения | should_read_message (чаты/каналы) |
| P2 | Каналы и чаты | Чтение из каналов (не только ЛС) |
| P3 | Таймауты и reconnect | Ошибки API, восстановление |
| P3 | Групповые чаты | Сообщения из групп |

### 8.2. Модули

| Приоритет | Тест | Описание |
|-----------|------|----------|
| P1 | job_matcher | Подбор вакансий (бизнес-логика) |
| P2 | classifier | AI-классификация текстов |
| P2 | notifications | Email уведомления |
| P3 | media | Загрузка/скачивание файлов |
| P3 | users | Профили пользователей |

### 8.3. Performance и надёжность

| Приоритет | Тест | Описание |
|-----------|------|----------|
| P2 | Нагрузка | 100+ сообщений параллельно |
| P2 | Стабильность | 1000 сообщений без ошибок |
| P3 | Recovery | Перезапуск после сбоя БД |
| P3 | Конкурентность | Параллельные запросы к API |

---

## 9. Troubleshooting

### 9.1. Частые ошибки

**Ошибка:** `TelegramClient not connected`
- **Причина:** Session-файл не создан или истёк
- **Решение:** Удалить session, запустить с `--create-session`

**Ошибка:** `Bot token invalid`
- **Причина:** Неверный токен бота
- **Решение:** Проверить TG_BOT_TOKEN в .env.test

**Ошибка:** `Database connection failed`
- **Причина:** PostgreSQL недоступен
- **Решение:** Запустить БД (docker-compose up db)

**Ошибка:** `Phone code invalid`
- **Причина:** Неверный SMS-код
- **Решение:** Запросить новый код, проверить номер

### 9.2. Логирование

```bash
# Полное логирование Telethon
pytest tests/e2e/ -v --log-cli-level=DEBUG -o log_cli=true

# Логирование только ошибок
pytest tests/e2e/ -v --log-cli-level=ERROR
```

### 9.3. Отладка

```python
# Добавить в тест
import logging
logging.basicConfig(level=logging.DEBUG)

# Telethon логи
logging.getLogger('telethon').setLevel(logging.DEBUG)

# aiogram логи
logging.getLogger('aiogram').setLevel(logging.DEBUG)
```

---

## 10. Заключение

### 10.1. Итоги

Данный дизайн обеспечивает:
- ✅ Реальную интеграцию с Telegram API
- ✅ Покрытие критических пользовательских сценариев
- ✅ Изоляцию тестов при приемлемой скорости
- ✅ Путь для будущих расширений

### 10.2. Следующие шаги

1. ✅ Утверждение дизайн-документа
2. ⏳ Создание `.env.test.example`
3. ⏳ Реализация фикстур (conftest.py)
4. ⏳ Написание 5 MVP тестов
5. ⏳ Документация в `docs/e2e-testing.md`
6. ⏳ CI/CD интеграция

---

## Приложения

### A. Ссылки на документацию

- [STYLEGUIDE.md](../../STYLEGUIDE.md) — стиль кода
- [docs/architecture.md](../architecture.md) — архитектура проекта
- [docs/bus.md](../bus.md) — шина сообщений
- [tests/conftest.py](../../tests/conftest.py) — текущие фикстуры

### B. Глоссарий

| Термин | Определение |
|--------|-------------|
| **E2E** | End-to-End тестирование (сквозное) |
| **Telethon** | Python-клиент Telegram User API |
| **aiogram** | Python-фреймворк для Telegram Bot API |
| **Session** | Файл сессии Telegram (хранит auth-данные) |
| **MessageBus** | Шина сообщений для межмодульного взаимодействия |
