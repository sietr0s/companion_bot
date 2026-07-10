# Документация модулей ms_starter

Этот каталог содержит подробную документацию по каждому бизнес-модулю проекта ms_starter.

## Список модулей

| Модуль | Описание | Топики |
|--------|----------|--------|
| [auth](./auth.md) | Регистрация, вход, JWT-токены, управление аккаунтами | `user.registered`, `user.logged_in`, `user.deleted` |
| [users](./users.md) | Профили пользователей, Telegram-профили | `profile.created`, `profile.updated`, `profile.deleted` |
| [telegram_clients](./telegram_clients.md) | Подключение к Telegram через Telethon, управление сессиями | `tg.message.received`, `tg.message.send`, `tg.account.connected` |
| [job_bot](./job_bot.md) | Telegram-бот на aiogram, шлюз сообщений | `bot.message.incoming`, `bot.message.outgoing` |
| [job_matcher](./job_matcher.md) | Подбор вакансий, подписки, классификация | `text.classify.request`, `job.offer.classified`, `notification.send` |
| [media](./media.md) | Загрузка, хранение, скачивание файлов | `media.uploaded`, `media.deleted` |
| [notifications](./notifications.md) | Email/SMS уведомления, шаблоны Jinja2 | `notification.send` |
| [classifier](./classifier.md) | AI-классификация текстов (BART), извлечение сущностей | `text.classify.completed` |

## Архитектура модулей

### Принципы Modular Monolith

1. **Изоляция модулей** — модули не импортируют друг друга напрямую
2. **Связь через шину** — взаимодействие только через события (MessageBus)
3. **Интерфейсы (Protocol)** — зависимости между модулями через абстракции
4. **Нет ForeignKey между модулями** — каждая таблица принадлежит одному модулю
5. **DI-контейнер** — FastAPI Depends для внедрения зависимостей
6. **Единый реестр топиков** — все топики определены в `BusTopics`

### Структура модуля

```
modules/<module_name>/
├── models.py           # SQLAlchemy модели
├── repository.py       # Репозиторий с кастомными методами
├── service.py          # Бизнес-логика
├── router.py           # HTTP роуты (публичные/внутренние)
├── handlers.py         # Обработчики событий шины
├── dependencies.py     # DI-фабрики модуля
├── constants.py        # Константы, enum, сообщения об ошибках
├── schemas/
│   ├── events.py       # События шины (Pydantic)
│   ├── public/         # Публичные API схемы
│   └── internal/       # Внутренние API схемы
└── routers/
    ├── public.py       # Публичные HTTP роуты
    └── internal.py     # Внутренние HTTP роуты
```

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

## Карта взаимосвязей модулей

```
┌─────────────┐
│    auth     │───────┐
└─────────────┘       │
      │               ▼
      │         ┌─────────────┐
      └────────▶│    users    │
      │         └─────────────┘
      │               │
      │               ▼
      │         ┌─────────────┐
      │         │notifications│
      │         └─────────────┘
      │
      │         ┌─────────────┐
      └────────▶│telegram_    │
                │  clients    │
                └─────────────┘
                      │
                      ▼
                ┌─────────────┐
                │   media     │
                └─────────────┘


┌─────────────┐
│  classifier │◀──────┐
└─────────────┘       │
      ▲               │
      │               ▼
      │         ┌─────────────┐
      └─────────│ job_matcher │
                └─────────────┘
                      ▲
                      │
                ┌─────────────┐
                │  job_bot    │
                └─────────────┘
```

## Топики шины (сводная таблица)

| Топик | Публикует | Подписывается | Описание |
|-------|-----------|---------------|----------|
| `user.registered` | auth | users, notifications | Пользователь зарегистрирован |
| `user.logged_in` | auth | users | Пользователь вошёл |
| `user.deleted` | auth | — | Аккаунт удалён |
| `profile.created` | users | — | Профиль создан |
| `profile.updated` | users | — | Профиль обновлён |
| `profile.deleted` | users | — | Профиль удалён |
| `tg.message.received` | telegram_clients | job_matcher | Входящее сообщение из Telegram |
| `tg.message.send` | — | telegram_clients | Отправить сообщение через аккаунт |
| `tg.account.connected` | telegram_clients | — | Аккаунт подключён |
| `tg.account.disconnected` | telegram_clients | — | Аккаунт отключён |
| `bot.message.incoming` | job_bot | job_matcher | Входящее сообщение от пользователя |
| `bot.message.outgoing` | job_matcher | job_bot | Исходящее сообщение пользователю |
| `text.classify.request` | job_matcher | classifier | Запрос на классификацию |
| `text.classify.completed` | classifier | job_matcher | Результат классификации |
| `job.offer.classified` | classifier | job_matcher | Вакансия классифицирована |
| `notification.send` | job_matcher | notifications | Отправка уведомления |
| `media.uploaded` | media | — | Файл загружен |
| `media.deleted` | media | — | Файл удалён |

## Дополнительные материалы

- [STYLEGUIDE.md](../../STYLEGUIDE.md) — стиль кода, паттерны, примеры
- [docs/architecture.md](../architecture.md) — архитектура проекта
- [docs/api.md](../api.md) — все HTTP-эндпоинты
- [docs/database.md](../database.md) — модели БД, ER-диаграмма
- [docs/bus.md](../bus.md) — шина сообщений, топики, события
- [docs/new-module.md](../new-module.md) — создание нового модуля
- [docs/deployment.md](../deployment.md) — развёртывание (Docker, Kafka)
