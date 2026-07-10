# E2E тестирование ms_starter

**Последнее обновление:** 2026-07-09

---

## 1. Overview

### 1.1. Что такое E2E тесты в этом проекте?

E2E (End-to-End) тесты проверяют **сквозное взаимодействие** между модулями системы через **реальный Telegram API**:

- ✅ **Бот тестируется через Telethon User API** — тестовый пользователь отправляет сообщения боту
- ✅ **telegram_clients тестируется через тестового бота** — бот шлёт сообщения, система обрабатывает
- ✅ **Реальные session-файлы** Telegram (не моки)
- ✅ **PostgreSQL** для тестирования БД
- ✅ **In-memory шина** для событий между модулями

### 1.2. Чем отличаются от других тестов?

| Тип тестов | Инструменты | Telegram | БД | Скорость |
|------------|-------------|----------|-----|----------|
| **Unit** | pytest, фикстуры | Моки | SQLite in-memory | ⚡⚡⚡ |
| **Интеграционные** | pytest, httpx | Моки | SQLite in-memory | ⚡⚡ |
| **E2E** | pytest, Telethon, aiogram | **Реальный API** | PostgreSQL | ⚡ |

### 1.3. Когда запускать E2E тесты?

- ✅ Перед релизом (pre-production)
- ✅ После интеграции новых модулей
- ✅ Для проверки критических пользовательских сценариев
- ❌ Не для каждого коммита (слишком медленно)

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

### 2.2. Структура тестов

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
├── utils.py                      # Вспомогательные функции
├── conftest.py                   # E2E фикстуры
└── sessions/                     # Session-файлы (.gitignore)
    └── test_e2e.session
```

---

## 3. Настройка окружения

### 3.1. Требования

- Python 3.12+
- PostgreSQL 15+
- Telegram API credentials (см. ниже)

### 3.2. Установка зависимостей

```bash
# Убедитесь, что все зависимости установлены
pip install -r requirements.txt

# Для E2E тестов нужны дополнительные пакеты
pip install pytest-asyncio telethon aiogram httpx
```

### 3.3. Создание .env.test

Скопируйте `.env.test.example` в `.env.test` и заполните:

```bash
cp .env.test.example .env.test
```

**Необходимые переменные:**

```ini
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

### 3.4. Получение Telegram credentials

#### TG_API_ID и TG_API_HASH

1. Зайти на https://my.telegram.org
2. Авторизоваться по номеру телефона
3. Перейти в **"API development tools"**
4. Нажать **"Create application"**
5. Заполнить форму:
   - **Application title**: `ms_starter_e2e_tests`
   - **Short name**: `mse2e`
   - **Platform**: выбрать `Desktop`
6. Скопировать:
   - **App api_id** → `TG_API_ID`
   - **App api_hash** → `TG_API_HASH`

#### TG_BOT_TOKEN

1. Открыть @BotFather в Telegram
2. Отправить команду `/newbot`
3. Ввести имя бота (например, `ms_starter E2E Test Bot`)
4. Ввести username бота (обязательно оканчивается на `bot`, например `ms_starter_e2e_test_bot`)
5. Скопировать токен → `TG_BOT_TOKEN`

#### TG_TEST_USER_PHONE

- Использовать существующий тестовый Telegram-аккаунт
- **Важно:** Не используйте основной личный аккаунт!
- Рекомендуется создать отдельный тестовый аккаунт

### 3.5. Первая аутентификация (создание session)

Первый запуск тестов потребует аутентификации в Telegram:

```bash
# Создать директорию для session-файлов
mkdir -p /tmp/ms_starter_e2e_tests

# Запустить тест на создание session
pytest tests/e2e/scenarios/test_registration.py::test_create_session -v
```

**Процесс:**
1. Тест запросит номер телефона (если не указан в .env.test)
2. Telegram отправит SMS-код
3. Ввести код в консоль
4. Если включён 2FA — ввести пароль
5. Session сохранится в `TG_TEST_SESSION_PATH`

**Последующие запуски** будут использовать сохранённую сессию.

---

## 4. Запуск тестов

### 4.1. Базовые команды

```bash
# Запуск всех E2E тестов
pytest tests/e2e/ -v --env-file=.env.test

# Запуск конкретного сценария
pytest tests/e2e/scenarios/test_registration.py -v

# Запуск одного теста
pytest tests/e2e/scenarios/test_registration.py::test_registration_flow -v

# Запуск с логированием Telethon
pytest tests/e2e/ -v --log-cli-level=DEBUG -o log_cli=true

# Запуск без очистки БД (для отладки)
pytest tests/e2e/ -v --no-db-cleanup
```

### 4.2. Фильтрация тестов

```bash
# По меткам
pytest tests/e2e/ -v -m "e2e and telegram"

# По имени
pytest tests/e2e/ -v -k "registration"

# Исключить медленные тесты
pytest tests/e2e/ -v -m "not slow"
```

### 4.3. Параллельный запуск

```bash
# Установить pytest-xdist
pip install pytest-xdist

# Запустить в 4 процесса
pytest tests/e2e/ -v -n 4
```

**Важно:** Параллельный запуск может вызвать конфликты при работе с одним session-файлом. Используйте с осторожностью.

---

## 5. Описание MVP тестов (5 сценариев)

### Тест 1: Регистрация и подключение Telegram

**Файл:** `test_registration.py`

**Что проверяет:**
- Регистрация пользователя через API
- Двухэтапная аутентификация Telegram (SMS + 2FA)
- Сохранение session-файла
- Создание записи в БД

**Сценарий:**
```
1. POST /public/auth/register → User создан
2. POST /public/telegram/auth/phone → SMS отправлен
3. POST /public/telegram/auth/code → Код принят
4. [Если 2FA] POST /public/telegram/auth/password → Пароль принят
5. Проверка: аккаунт в БД, status="connected"
6. Проверка: session-файл существует
```

**Использование:**
```bash
pytest tests/e2e/scenarios/test_registration.py -v
```

---

### Тест 2: Входящее сообщение от бота

**Файл:** `test_incoming_message.py`

**Что проверяет:**
- Обработку входящих сообщений из Telegram
- Публикацию события `tg.message.received` в шину
- Извлечение медиа из сообщений (если есть)

**Сценарий:**
```
1. aiogram Bot → отправляет сообщение тестовому аккаунту
2. TelegramClientManager → получает сообщение
3. Проверка настроек чтения (should_read_message)
4. Публикация tg.message.received в шину
5. Проверка: событие в шине, данные корректны
```

**Использование:**
```bash
pytest tests/e2e/scenarios/test_incoming_message.py -v
```

---

### Тест 3: Исходящее сообщение через Telegram

**Файл:** `test_outgoing_message.py`

**Что проверяет:**
- Обработку исходящих сообщений через шину
- Отправку через TelegramClientManager
- Доставку сообщения

**Сценарий:**
```
1. Публикация tg.message.send в шину
2. TelegramClientManager → отправляет сообщение
3. Telethon → проверяет получение
4. Проверка: message_id корректен
```

**Использование:**
```bash
pytest tests/e2e/scenarios/test_outgoing_message.py -v
```

---

### Тест 4: Команда боту (/start)

**Файл:** `test_bot_command.py`

**Что проверяет:**
- Получение команд ботом
- Публикацию `bot.message.incoming`
- Обработку job_matcher
- Ответ бота пользователю

**Сценарий:**
```
1. Telethon → пользователь отправляет /start боту
2. aiogram → получает команду
3. Публикация bot.message.incoming в шину
4. job_matcher → обрабатывает команду
5. Публикация bot.message.outgoing
6. Бот → отправляет ответ
7. Telethon → проверяет ответ
```

**Использование:**
```bash
pytest tests/e2e/scenarios/test_bot_command.py -v
```

---

### Тест 5: Полный цикл match

**Файл:** `test_full_match_cycle.py`

**Что проверяет:**
- Сквозной сценарий: сообщение → классификация → подбор → ответ
- Интеграцию всех модулей
- Корректность бизнес-логики

**Сценарий:**
```
1. Telethon → сообщение боту ("ищу вакансию Python разработчика")
2. aiagram → получает сообщение
3. bot.message.incoming → шина
4. job_matcher → классификация текста
5. job_matcher → подбор вакансий из БД
6. bot.message.outgoing → шина
7. Бот → ответ с вакансиями
8. Telethon → проверка ответа
```

**Использование:**
```bash
pytest tests/e2e/scenarios/test_full_match_cycle.py -v
```

---

## 6. Backlog будущих расширений

### 6.1. Telegram-сценарии

| Приоритет | Тест | Описание | Статус |
|-----------|------|----------|--------|
| P1 | 2FA аутентификация | Тест flow с паролем | 🔴 Не написан |
| P1 | Загрузка медиа | Проверка вложений из сообщений | 🔴 Не написан |
| P2 | Настройки чтения | should_read_message (чаты/каналы) | 🔴 Не написан |
| P2 | Каналы и чаты | Чтение из каналов (не только ЛС) | 🔴 Не написан |
| P3 | Таймауты и reconnect | Ошибки API, восстановление | 🔴 Не написан |
| P3 | Групповые чаты | Сообщения из групп | 🔴 Не написан |

### 6.2. Модули

| Приоритет | Тест | Описание | Статус |
|-----------|------|----------|--------|
| P1 | job_matcher | Подбор вакансий (бизнес-логика) | 🔴 Не написан |
| P2 | classifier | AI-классификация текстов | 🔴 Не написан |
| P2 | notifications | Email уведомления | 🔴 Не написан |
| P3 | media | Загрузка/скачивание файлов | 🔴 Не написан |
| P3 | users | Профили пользователей | 🔴 Не написан |

### 6.3. Performance и надёжность

| Приоритет | Тест | Описание | Статус |
|-----------|------|----------|--------|
| P2 | Нагрузка | 100+ сообщений параллельно | 🔴 Не написан |
| P2 | Стабильность | 1000 сообщений без ошибок | 🔴 Не написан |
| P3 | Recovery | Перезапуск после сбоя БД | 🔴 Не написан |
| P3 | Конкурентность | Параллельные запросы к API | 🔴 Не написан |

---

## 7. Troubleshooting

### 7.1. Частые ошибки

#### `TelegramClient not connected`

**Симптомы:**
```
telethon.errors.rpcerrorlist.AuthKeyUnregisteredError: ...
```

**Причины:**
- Session-файл не создан или истёк
- Session удалён Telegram (долгий простой)

**Решение:**
```bash
# Удалить старый session
rm /tmp/ms_starter_e2e_tests/test_e2e.session*

# Запустить создание нового session
pytest tests/e2e/scenarios/test_registration.py::test_create_session -v
```

---

#### `Bot token invalid`

**Симптомы:**
```
aiogram.utils.exceptions.ValidationError: Token is invalid
```

**Причины:**
- Неверный токен в .env.test
- Бот заблокирован Telegram

**Решение:**
1. Проверить `TG_BOT_TOKEN` в .env.test
2. Создать нового бота через @BotFather
3. Обновить токен в .env.test

---

#### `Database connection failed`

**Симптомы:**
```
asyncpg.exceptions.CannotConnectNowError: ...
```

**Причины:**
- PostgreSQL недоступен
- Неверный DATABASE_URL

**Решение:**
```bash
# Запустить PostgreSQL
docker-compose up db -d

# Проверить подключение
psql postgresql://postgres:postgres@localhost:5432/ms_starter_e2e
```

---

#### `Phone code invalid`

**Симптомы:**
```
telethon.errors.rpcerrorlist.PhoneCodeInvalidError: ...
```

**Причины:**
- Введён неверный SMS-код
- Код устарел (таймаут)

**Решение:**
1. Запросить новый код (кнопка в Telegram)
2. Проверить номер телефона в .env.test
3. Повторить попытку

---

### 7.2. Логирование

**Полное логирование:**
```bash
pytest tests/e2e/ -v --log-cli-level=DEBUG -o log_cli=true
```

**Только Telethon:**
```bash
pytest tests/e2e/ -v \
  -o log_cli=true \
  -o logger_telethon=DEBUG
```

**Только aiogram:**
```bash
pytest tests/e2e/ -v \
  -o log_cli=true \
  -o logger_aiogram=DEBUG
```

---

### 7.3. Отладка

**Добавить отладочное логирование в тест:**
```python
import logging

logging.basicConfig(level=logging.DEBUG)
logging.getLogger('telethon').setLevel(logging.DEBUG)
logging.getLogger('aiogram').setLevel(logging.DEBUG)
```

**Использовать pdb:**
```python
def test_something():
    import pdb; pdb.set_trace()
    # ... код теста
```

---

## 8. FAQ

### 8.1. Можно ли запускать E2E тесты в CI?

**Да**, но с учётом особенностей:

```yaml
# .github/workflows/e2e-tests.yml
name: E2E Tests

on:
  push:
    branches: [master, release/*]
  workflow_dispatch:  # Запуск по требованию

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

**Важно:**
- Храните credentials в **GitHub Secrets**
- Запускайте **по требованию** (`workflow_dispatch`), не на каждый коммит
- Используйте **отдельный тестовый аккаунт** Telegram

---

### 8.2. Как долго выполняются тесты?

| Количество тестов | Время выполнения |
|-------------------|------------------|
| 1 тест | ~5-10 секунд |
| MVP (5 тестов) | ~30-60 секунд |
| Все (будущие 20+) | ~3-5 минут |

---

### 8.3. Можно ли запускать тесты без реального Telegram?

**Нет**, E2E тесты по дизайну используют реальный Telegram API.

Для тестирования без Telegram используйте:
- **Unit тесты** — моки Telethon и aiogram
- **Интеграционные тесты** — моки с проверкой шины

---

### 8.4. Что делать если тесты падают нестабильно?

**Причины нестабильности:**
1. **Telegram API rate limits** — слишком частые запросы
2. **Проблемы с сетью** — таймауты соединения
3. **Блокировки** — аккаунт/бот временно ограничен

**Решения:**
- Добавить `@pytest.mark.flaky(retries=3)` для нестабильных тестов
- Увеличить таймауты в коннектах
- Запускать реже (не на каждый коммит)

---

## 9. Дополнительные ресурсы

### 9.1. Документация проекта

- [Дизайн-документ](./superpowers/specs/2026-07-09-e2e-testing-design.md) — полная архитектура
- [STYLEGUIDE.md](../STYLEGUIDE.md) — стиль кода
- [docs/architecture.md](./architecture.md) — архитектура проекта
- [docs/bus.md](./bus.md) — шина сообщений

### 9.2. Внешние ресурсы

- [Telethon документация](https://docs.telethon.dev/)
- [aiogram документация](https://docs.aiogram.dev/)
- [pytest документация](https://docs.pytest.org/)
- [Telegram API](https://core.telegram.org/api)

---

## 10. История изменений

| Дата | Изменение | Автор |
|------|-----------|-------|
| 2026-07-09 | Initial version | GigaCode |
