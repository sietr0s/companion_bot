# Дизайн: Telegram Bot Microservice

**Дата:** 2026-07-01  
**Статус:** Утверждён  
**Связанные задачи:** Создание микросервиса телеграм-бота на основе архитектуры Modular Monolith

---

## Обзор

Микросервис телеграм-бота на **Python + FastAPI + aiogram 3.x** для обработки команд пользователей, автоматической регистрации через `/start` и отправки уведомлений из основного приложения (ms_starter).

### Ключевые особенности

- **Модульная архитектура** — каждый хендлер в отдельном файле
- **Гибридная интеграция** — REST API для синхронных запросов, Kafka/шина для событий
- **Поддержка Polling и Webhook** — переключение через конфигурацию
- **Telegram-авторизация** — автоматическое создание пользователя и профиля при первом запуске
- **Отдельная модель Telegram** — foreign key из UserProfile на Telegram

---

## Архитектура

### Структура проекта

```
bot_service/
├── src/
│   ├── main.py                 # Точка входа, lifespan
│   ├── config.py               # Pydantic Settings (BOT_TOKEN, BOT_MODE, etc.)
│   ├── clients/
│   │   ├── __init__.py
│   │   ├── base.py             # Базовый HTTP-клиент
│   │   └── main_api.py         # Клиент к ms_starter (REST API)
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── bot.py              # init_bot(), get_bot(), create_dispatcher()
│   │   └── middlewares.py      # Логирование, авторизация
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── base.py             # BaseHandler (DI для main_api и bot)
│   │   ├── start.py            # /start, /help — регистрация
│   │   ├── profile.py          # /profile, /settings
│   │   └── bot_messages.py     # Обработчик события bot.message.send
│   ├── events/
│   │   ├── __init__.py
│   │   └── bot_message.py      # BotMessageSend(BaseEvent)
│   ├── keyboards/
│   │   ├── __init__.py
│   │   └── main_menu.py        # Inline-клавиатура
│   └── api/
│       ├── __init__.py
│       └── routes.py           # FastAPI роуты (/health, /webhook, /bot/messages/send)
├── tests/
│   ├── conftest.py
│   ├── handlers/
│   └── services/
├── requirements.txt
├── docker-compose.yml
└── README.md
```

### Компоненты

| Компонент | Описание | Зависимости |
|-----------|----------|-------------|
| `bot.py` | Инициализация Bot + Dispatcher | aiogram |
| `registry.py` | Реестр команд (имя → хендлер) | - |
| `handlers/base.py` | Базовый класс для хендлеров | main_api, bot |
| `handlers/start.py` | Обработчик `/start` | bot, keyboards, main_api |
| `handlers/profile.py` | Обработчик `/profile` | bot, main_api |
| `handlers/bot_messages.py` | Обработчик события `bot.message.send` | bot |
| `events/bot_message.py` | Событие отправки сообщения | BaseEvent |
| `clients/main_api.py` | HTTP-клиент к ms_starter | httpx |
| `keyboards/main_menu.py` | Главная клавиатура | aiogram.types |

---

## Модели данных

### ms_starter (основное приложение)

#### Telegram (новая модель)

```python
class Telegram(BaseModel):
    __tablename__ = "telegram"

    id: Mapped[uuid.UUID]
    telegram_id: Mapped[str]  # unique, index
    telegram_username: Mapped[str | None]
    telegram_first_name: Mapped[str | None]
    telegram_last_name: Mapped[str | None]

    user_profile: Mapped["UserProfile | None"] = relationship(
        back_populates="telegram", uselist=False
    )
```

#### UserProfile (обновлённая)

```python
class UserProfile(BaseModel):
    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID]
    auth_id: Mapped[uuid.UUID]  # unique, index
    first_name: Mapped[str | None]
    last_name: Mapped[str | None]
    email: Mapped[str | None]
    avatar_url: Mapped[str | None]
    bio: Mapped[str | None]

    telegram_id: Mapped[uuid.UUID | None]  # FK → Telegram.id
    telegram: Mapped[Telegram | None] = relationship(
        back_populates="user_profile", uselist=False
    )
```

### bot_service (события)

#### BotMessageSend

```python
class BotMessageSend(BaseEvent):
    event_name: str = "bot.message.send"
    telegram_id: str
    text: str
    parse_mode: str = "HTML"
    reply_markup: dict | None = None
```

---

## Интеграция с ms_starter

### Направления взаимодействия

| Направление | Механизм | Пример |
|-------------|----------|--------|
| **Бот → ms_starter** | REST API (httpx) | Создать пользователя, получить профиль |
| **ms_starter → Бот** | Kafka события (шина) | Отправить уведомление через бота |

### Топики шины

Добавить в `src/core/bus_topics.py` (ms_starter):

```python
class BusTopics(StrEnum):
    # ... существующие топики ...
    BOT_MESSAGE_SEND = "bot.message.send"  # Отправить сообщение через бота
```

### REST API эндпоинты

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/auth/register` | Создать пользователя (identifier_type="telegram") |
| POST | `/users/` | Создать профиль пользователя |
| POST | `/users/telegram-profiles/` | Создать Telegram-профиль |
| GET | `/users/telegram-profiles/?filters=...` | Найти Telegram по telegram_id |
| POST | `/bot/messages/send` | Отправить сообщение (альтернатива шине) |

---

## Жизненный цикл

### 1. Запуск бота (main.py)

```python
async def main():
    logging.basicConfig(level=logging.INFO)

    bot = init_bot()  # Инициализация Bot
    dp = create_dispatcher()  # Регистрация роутеров

    app.state.dispatcher = dp  # Для webhook

    try:
        await start_bot(bot, dp)  # polling или webhook
    finally:
        await bot.session.close()
```

### 2. Команда /start (handlers/start.py)

```
Пользователь → /start
    ↓
StartHandler.handle()
    ↓
1. Проверить: есть ли пользователь по telegram_id?
    ↓ (нет)
2. Создать AuthAccount (identifier_type="telegram")
    ↓
3. Создать UserProfile
    ↓
4. Создать Telegram + связать FK
    ↓
5. Показать главное меню
```

### 3. Отправка уведомления (ms_starter → бот)

```
NotificationService.send_notification(channel="telegram")
    ↓
Публикация события BotMessageSend в шину
    ↓
BotMessageHandler.handle() (в боте)
    ↓
bot.send_message(chat_id=telegram_id, text=...)
```

---

## Конфигурация

### .env.example

```bash
# Режим работы бота: polling или webhook
BOT_MODE=polling

# Telegram Bot Token
BOT_TOKEN=your_bot_token_here

# Polling настройки
BOT_POLLING_TIMEOUT=30
BOT_POLLING_ALLOWED_UPDATES=message,edited_message,callback_query

# Webhook настройки
BOT_WEBHOOK_URL=https://your-domain.com
BOT_WEBHOOK_PATH=/webhook
BOT_WEBHOOK_PORT=8000

# Main API
MAIN_API_URL=http://localhost:8000
MAIN_API_TIMEOUT=10.0

# Kafka (опционально)
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_GROUP_ID=telegram-bot
```

### Pydantic Settings (config.py)

```python
class BotMode(str, Enum):
    POLLING = "polling"
    WEBHOOK = "webhook"


class Settings(BaseSettings):
    BOT_TOKEN: str = ""
    BOT_MODE: BotMode = BotMode.POLLING

    BOT_POLLING_TIMEOUT: int = 30
    BOT_POLLING_ALLOWED_UPDATES: str = "message,edited_message,callback_query"

    BOT_WEBHOOK_URL: str = ""
    BOT_WEBHOOK_PATH: str = "/webhook"
    BOT_WEBHOOK_PORT: int = 8000

    MAIN_API_URL: str = "http://localhost:8000"
    MAIN_API_TIMEOUT: float = 10.0

    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_GROUP_ID: str = "telegram-bot"
```

---

## Обработка ошибок

### Грейсфул деградейшн

```python
# В хендлерах — без try/except (ошибки логируются глобально)
async def handle(self, message: Message):
    telegram_id = str(message.from_user.id)
    auth_data = await self.main_api.create_telegram_user(telegram_id)
    # Если ошибка — логгер.exception() в базовом классе
```

### Глобальный логгер

```python
# middlewares.py
class LoggingMiddleware:
    async def __call__(self, event, handler):
        try:
            return await handler(event)
        except Exception:
            logger.exception("Ошибка в хендлере")
            raise
```

---

## Тестирование

### Юнит-тесты

```python
# tests/handlers/test_start.py
@pytest.mark.asyncio
async def test_start_new_user(main_api_mock, bot_mock):
    handler = StartHandler(main_api_mock)
    message = Mock(from_user=Mock(id=123, first_name="Ivan"))

    await handler.handle(message)

    main_api_mock.create_telegram_user.assert_called_once_with("123")
    main_api_mock.create_user_profile.assert_called_once()
    main_api_mock.create_telegram_profile.assert_called_once()
```

### Интеграционные тесты

```python
# tests/services/test_main_api.py
@pytest.mark.asyncio
async def test_create_telegram_user(client):
    result = await client.create_telegram_user("123")
    assert "auth_id" in result
    assert "access_token" in result
```

---

## Миграции БД

### Alembic migration

```python
# alembic/versions/xxxx_add_telegram_model.py

def upgrade():
    # 1. Создать таблицу telegram
    op.create_table(
        "telegram",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("telegram_id", sa.String(50), nullable=False),
        sa.Column("telegram_username", sa.String(100), nullable=True),
        sa.Column("telegram_first_name", sa.String(100), nullable=True),
        sa.Column("telegram_last_name", sa.String(100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_telegram_telegram_id", "telegram", ["telegram_id"], unique=True)

    # 2. Добавить FK в user_profiles
    op.add_column("user_profiles", sa.Column("telegram_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_user_profiles_telegram", "user_profiles", "telegram",
                          ["telegram_id"], ["id"])


def downgrade():
    op.drop_constraint("fk_user_profiles_telegram", "user_profiles", type_="foreignkey")
    op.drop_column("user_profiles", "telegram_id")
    op.drop_table("telegram")
```

---

## Docker Compose

```yaml
version: '3.8'

services:
  bot:
    build: .
    container_name: telegram_bot
    environment:
      - BOT_TOKEN=${BOT_TOKEN:-}
      - BOT_MODE=${BOT_MODE:-polling}
      - BOT_POLLING_TIMEOUT=30
      - BOT_WEBHOOK_URL=${BOT_WEBHOOK_URL:-}
      - MAIN_API_URL=http://ms_starter_app:8000
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
    depends_on:
      - ms_starter_app
    networks:
      - ms_network
    restart: unless-stopped
    ports:
      - "${BOT_WEBHOOK_PORT:-8000}:8000"  # Только для webhook

  ms_starter_app:
    # ... существующий сервис ...

  kafka:
    # ... существующий сервис ...
```

---

## План реализации

1. **Настройка проекта**
   - Создать структуру директорий
   - Настроить requirements.txt (aiogram, fastapi, httpx, pydantic-settings)
   - Настроить docker-compose.yml

2. **Конфигурация и базовая инфраструктура**
   - Реализовать config.py с BotMode enum
   - Реализовать bot/bot.py (init_bot, create_dispatcher, start_bot)
   - Реализовать clients/base.py и clients/main_api.py

3. **Модели и миграции в ms_starter**
   - Добавить модель Telegram
   - Обновить UserProfile с FK на Telegram
   - Создать Alembic миграцию

4. **Хендлеры**
   - Реализовать handlers/base.py
   - Реализовать handlers/start.py (/start, регистрация)
   - Реализовать handlers/profile.py (/profile, /settings)
   - Реализовать handlers/bot_messages.py (обработчик события)

5. **События и интеграция**
   - Реализовать events/bot_message.py
   - Добавить BusTopics.BOT_MESSAGE_SEND в ms_starter
   - Реализовать internal.py роуты для telegram-profiles
   - Обновить NotificationService для отправки через бота

6. **Ключи и UI**
   - Реализовать keyboards/main_menu.py

7. **API роуты**
   - Реализовать api/routes.py (/health, /webhook, /bot/messages/send)

8. **Тесты**
   - Написать юнит-тесты для хендлеров
   - Написать интеграционные тесты для клиентов

9. **Документация**
   - Написать README.md
   - Написать .env.example

---

## Критерии готовности

- [ ] Бот запускается в режиме polling
- [ ] Бот запускается в режиме webhook
- [ ] Команда `/start` создаёт пользователя и Telegram-профиль
- [ ] Команда `/profile` показывает данные пользователя
- [ ] ms_starter может отправить уведомление через бота (шина)
- [ ] ms_starter может отправить уведомление через бота (REST API)
- [ ] Все тесты проходят
- [ ] Линтер не находит ошибок (ruff)

---

## Риски и ограничения

| Риск | Влияние | Митигация |
|------|---------|-----------|
| Изменение API ms_starter | Бот перестанет работать | Версионирование API, контракты |
| Потеря сессии Telegram | Нужно переподключать | Хранить telegram_id в БД |
| Rate limiting Telegram | Ограничения на отправку | Queue + retry с backoff |
| Дублирование telegram_id | Ошибка при создании | Unique constraint в БД |

---

## Вопросы для обсуждения

- [x] Архитектура утверждена
- [x] Модели утверждены
- [ ] План реализации утверждён
- [ ] Приступаем к реализации?

---

**Следующий шаг:** После утверждения плана — invoke `writing-plans` skill для создания детального плана реализации.
