# Модуль JOB_BOT

**Расположение**: `src/modules/job_bot/`

## Назначение

Telegram-бот на aiogram: шлюз для входящих/исходящих сообщений. Не содержит бизнес-логики — только транспорт между Telegram и шиной сообщений.

## Архитектурная роль

**Важно**: Модуль не содержит бизнес-логики и не обрабатывает команды.

### Поток сообщений

```
Входящие (от пользователя):
  Telegram → aiogram handler → bot.message.incoming (шина) → job_matcher (обработка)

Исходящие (к пользователю):
  Любой модуль → bot.message.outgoing (шина) → job_bot handler → Telegram API
```

### Топики шины

| Топик | Направление | Кто публикует | Кто подписывается |
|-------|-------------|----------------|-------------------|
| `bot.message.incoming` | Входящее | job_bot (aiogram handler) | job_matcher |
| `bot.message.outgoing` | Исходящее | Любой модуль | job_bot (отправка) |

## Модели данных

Модуль не имеет собственных моделей БД. Использует модели из `job_matcher` через зависимости.

## Сервис

### BotService

**Расположение**: `src/modules/job_bot/service.py`

```python
class BotService:
    """Сервис отправки сообщений через бота"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
```

### Методы

#### send_message
```python
async def send_message(
    self,
    chat_id: int,
    text: str,
    keyboard: InlineKeyboardMarkup | ReplyKeyboardMarkup | None = None,
) -> None:
    """
    Отправка сообщения пользователю
    
    Параметры:
    - chat_id: ID чата в Telegram
    - text: Текст сообщения
    - keyboard: Inline или Reply клавиатура (опционально)
    """
```

#### send_offer
```python
async def send_offer(
    self,
    chat_id: int,
    title: str,
    description: str,
    tags: list[str],
    salary_from: int | None,
    salary_to: int | None,
    location: str | None,
) -> None:
    """
    Отправка вакансии с inline-кнопками
    
    - Форматирует текст вакансии
    - Добавляет inline-кнопки (откликнуться, пропустить)
    """
```

## Обработчики событий

**Расположение**: `src/modules/job_bot/handlers.py`

### Входящие сообщения (aiogram handlers)

```python
def register_incoming_handlers(bus: MessageBus) -> Router:
    """
    Регистрация aiogram-обработчиков для входящих сообщений.

    Все сообщения (команды и текст) публикуются в шину.
    Бизнес-логика обрабатывается подписчиками (job_matcher).
    """
    router = Router()

    @router.message()
    async def handle_incoming_message(message: Message) -> None:
        """Обработчик всех входящих сообщений — публикация в шину."""
        # Извлекаем команду из первого слова (если начинается с /)
        command = None
        if message.text and message.text.startswith("/"):
            command = message.text.split()[0].split("@")[0]

        event = BotMessageIncoming(
            chat_id=message.chat.id,
            text=message.text or "",
            command=command,
        )
        await bus.publish(BusTopics.BOT_MESSAGE_INCOMING, event.to_bus_dict())

    return router
```

### Исходящие сообщения (шина)

```python
def register_outgoing_handlers(bus: MessageBus, bot_service: BotService) -> None:
    """
    Регистрация обработчиков шины для исходящих сообщений.

    Подписка на bot.message.outgoing — отправка через Telegram API.
    """

    @bus.subscribe(BusTopics.BOT_MESSAGE_OUTGOING)
    async def handle_outgoing_message(message: dict) -> None:
        """Отправить сообщение пользователю через Telegram-бота."""
        chat_id = message.get("chat_id")
        text = message.get("text", "")
        keyboard = message.get("keyboard")

        if not chat_id or not text:
            logger.warning("Неполные данные для отправки: %s", message)
            return

        await bot_service.send_message(
            chat_id=int(chat_id),
            text=text,
            keyboard=keyboard,
        )
```

## Клавиатуры

**Расположение**: `src/modules/job_bot/keyboards.py`

### get_main_keyboard
```python
def get_main_keyboard() -> ReplyKeyboardMarkup:
    """
    Главное меню бота
    
    Кнопки:
    - 🔍 Поиск вакансий
    - 📬 Моя подписка
    - ⚙️ Настройки
    """
```

### get_subscription_inline_keyboard
```python
def get_subscription_inline_keyboard(
    subscription_id: UUID,
) -> InlineKeyboardMarkup:
    """
    Inline-клавиатура для управления подпиской
    
    Кнопки:
    - ✏️ Редактировать
    - 🗑️ Удалить
    """
```

### get_offer_inline_keyboard
```python
def get_offer_inline_keyboard(
    offer_id: UUID,
) -> InlineKeyboardMarkup:
    """
    Inline-клавиатура для вакансии
    
    Кнопки:
    - ✅ Откликнуться
    - ⏭️ Пропустить
    - 📤 Поделиться
    """
```

### get_confirm_keyboard
```python
def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура подтверждения
    
    Кнопки:
    - ✅ Подтвердить
    - ❌ Отмена
    """
```

## Тексты и шаблоны

**Расположение**: `src/modules/job_bot/texts.py`

### Приветствие

```python
WELCOME_MESSAGE = """
👋 Привет! Я бот для поиска вакансий.

Я помогаю находить интересные предложения из Telegram-каналов.

Команды:
/start - Запустить бота
/subscribe - Оформить подписку
/settings - Настройки
"""
```

### Кнопки главного меню

```python
MAIN_MENU_BUTTON_SEARCH = "🔍 Поиск вакансий"
MAIN_MENU_BUTTON_SUBSCRIPTION = "📬 Моя подписка"
MAIN_MENU_BUTTON_SETTINGS = "⚙️ Настройки"
```

### Шаблоны вакансий

```python
VACANCY_TEMPLATE = """
💼 **{title}**

📍 {location}
💰 {salary}

{description}

#tags: {tags}
"""

VACANCY_SALARY_TEMPLATE = "{salary_from} - {salary_to} ₽"
VACANCY_SALARY_FROM_TEMPLATE = "от {salary_from} ₽"
VACANCY_SALARY_TO_TEMPLATE = "до {salary_to} ₽"
```

### Сообщения об ошибках

```python
ERROR_NOT_FOUND = "❌ Не найдено"
ERROR_ACCESS_DENIED = "⛔ Доступ запрещён"
ERROR_INTERNAL = "⚠️ Внутренняя ошибка"
```

## События шины

### Публикации (исходящие)

#### BotMessageIncoming
```python
class BotMessageIncoming(BaseEvent):
    """Входящее сообщение от пользователя"""
    
    chat_id: int
    text: str
    username: str | None
    command: str | None
```

**Топик**: `bot.message.incoming`

**Когда публикуется:**
- При получении команды от пользователя

**Подписчики:**
- `job_matcher.handlers` — обработка команд

### Подписки (входящие)

#### BotMessageOutgoing
```python
class BotMessageOutgoing(BaseEvent):
    """Исходящее сообщение пользователю"""
    
    chat_id: int
    text: str
    keyboard: dict | None
```

**Топик**: `bot.message.outgoing`

**Когда публикуется:**
- Для отправки сообщения пользователю

**Подписчики:**
- `job_bot.handlers` — отправка через бота

## Запуск бота

**Расположение**: `src/modules/job_bot/bot.py`

### create_bot
```python
def create_bot(token: str) -> Bot:
    """
    Создание бота
    
    Параметры:
    - token: Токен бота из Telegram Bot API
    """
    return Bot(token=token)
```

### create_dispatcher
```python
def create_dispatcher(
    bus: MessageBus,
    bot_service: BotService,
) -> Dispatcher:
    """
    Создание диспетчера с обработчиками
    
    - Регистрирует обработчики команд
    - Подписывается на шину сообщений
    """
    dp = Dispatcher()
    
    # Регистрация обработчиков
    register_incoming_handlers(dp, bus)
    register_outgoing_handlers(dp, bot_service)
    
    return dp
```

### start_polling
```python
async def start_polling(bot: Bot, dp: Dispatcher) -> None:
    """
    Запуск polling-режима
    
    Используется для локальной разработки
    """
    await dp.start_polling(bot)
```

### start_webhook
```python
async def start_webhook(
    bot: Bot,
    dp: Dispatcher,
    webhook_url: str,
    webhook_secret: str,
) -> None:
    """
    Запуск webhook-режима
    
    Параметры:
    - webhook_url: URL для webhook
    - webhook_secret: Секретный токен для проверки
    
    Используется для production
    """
    await dp.start_webhook(
        bot=bot,
        path="/webhook/telegram",
        webhook_url=webhook_url,
        secret_token=webhook_secret,
    )
```

## DI-зависимости

**Расположение**: `src/modules/job_bot/dependencies.py`

```python
def get_job_offer_repository() -> JobOfferRepository:
    """
    Фабрика репозитория вакансий
    
    Обратите внимание: использует репозиторий из job_matcher!
    Это нарушение изоляции, требует рефакторинга.
    """
    from src.modules.job_matcher.repository import JobOfferRepository
    return JobOfferRepository()


def get_subscription_repository() -> SubscriptionRepository:
    """
    Фабрика репозитория подписок
    
    Обратите внимание: использует репозиторий из job_matcher!
    """
    from src.modules.job_matcher.repository import SubscriptionRepository
    return SubscriptionRepository()


def get_job_matcher_service(
    offer_repo: Annotated[JobOfferRepository, Depends(get_job_offer_repository)],
    sub_repo: Annotated[SubscriptionRepository, Depends(get_subscription_repository)],
    message_bus: Annotated[MessageBus, Depends(get_message_bus)],
) -> JobMatcherService:
    """Фабрика сервиса job_matcher"""
    from src.modules.job_matcher.service import JobMatcherService
    return JobMatcherService(
        repository=offer_repo,
        subscription_repository=sub_repo,
        message_bus=message_bus,
    )


def get_bot(token: str = settings.TG_BOT_TOKEN) -> Bot:
    """Фабрика бота"""
    return Bot(token=token)


def get_bot_service(bot: Annotated[Bot, Depends(get_bot)]) -> BotService:
    """Фабрика сервиса отправки"""
    return BotService(bot=bot)
```

## Взаимосвязи с другими модулями

### Зависит от

| Модуль | Тип | Описание |
|--------|-----|----------|
| `bus` | Шина | Публикация/подписка на события |
| `job_matcher` | Прямые импорты | **Нарушение изоляции!** Репозитории и сервисы |

### Используется

| Модуль | Тип | Описание |
|--------|-----|----------|
| `job_matcher` | Подписка | Обработка команд /start, /subscribe |

## Проблемные места

### Нарушение изоляции

**Проблема**: `job_bot/dependencies.py` напрямую импортирует репозитории из `job_matcher`:

```python
from src.modules.job_matcher.repository import JobOfferRepository, SubscriptionRepository
```

**Почему это плохо**:
- Нарушает принцип изоляции модулей
- Усложняет тестирование
- Затрудняет будущий вынос модулей в отдельные сервисы

**Возможные решения**:

1. **Переместить зависимости внутрь job_matcher**
   - job_bot только публикует события
   - job_matcher сам подписывается и использует свои репозитории

2. **Использовать шину для всех взаимодействий**
   - job_bot публикует `bot.command.subscribe`
   - job_matcher подписывается и создаёт подписку

3. **Создать абстрактный интерфейс**
   - Определить Protocol в job_bot
   - Реализовать в job_matcher

## Примеры использования

### Отправка сообщения через шину

```python
# В любом обработчике или сервисе
await message_bus.publish(
    BusTopics.BOT_MESSAGE_OUTGOING,
    BotMessageOutgoing(
        chat_id=123456789,
        text="Привет! Это тестовое сообщение.",
        keyboard=None,
    ).to_bus_dict(),
)
```

### Обработка команды /start

```python
# В job_bot/handlers.py
@dp.message(Command("start"))
async def handle_start(message: Message, bus: MessageBus):
    await bus.publish(
        BusTopics.BOT_MESSAGE_INCOMING,
        BotMessageIncoming(
            chat_id=message.chat.id,
            text="/start",
            username=message.from_user.username,
            command="start",
        ).to_bus_dict(),
    )
    
    await message.answer("Привет! Я бот для поиска вакансий.")
```

### Отправка вакансии

```python
# В job_matcher/handlers.py, после нахождения подходящей вакансии
await message_bus.publish(
    BusTopics.BOT_MESSAGE_OUTGOING,
    BotMessageOutgoing(
        chat_id=user_chat_id,
        text=f"💼 **{offer.title}**\n\n{offer.description}",
        keyboard=get_offer_inline_keyboard(offer.id).to_dict(),
    ).to_bus_dict(),
)
```

## Конфигурация

### Переменные окружения

```bash
# TG_BOT_TOKEN=123456789:ABCDEF123456789
TG_BOT_TOKEN=your_bot_token

# TG_BOT_WEBHOOK_URL=https://example.com/webhook/telegram
TG_BOT_WEBHOOK_URL=

# TG_BOT_WEBHOOK_SECRET=secret_token
TG_BOT_WEBHOOK_SECRET=
```

### Режимы работы

**Polling (разработка):**
```python
if settings.TG_BOT_POLLING:
    await start_polling(bot, dp)
```

**Webhook (production):**
```python
else:
    await start_webhook(
        bot, dp,
        webhook_url=settings.TG_BOT_WEBHOOK_URL,
        webhook_secret=settings.TG_BOT_WEBHOOK_SECRET,
    )
```

## Тестирование

**Расположение тестов**: `tests/modules/job_bot/`

### Фикстуры

```python
@pytest.fixture
def bot(token: str = "123456789:ABCDEF123456789"):
    return Bot(token=token)


@pytest.fixture
def bot_service(bot: Bot):
    return BotService(bot=bot)


@pytest.fixture
def dispatcher(bus: MessageBus, bot_service: BotService):
    return create_dispatcher(bus, bot_service)
```

### Пример теста

```python
async def test_send_message(bot_service: BotService, mock_bot: AsyncMock):
    await bot_service.send_message(
        chat_id=123456789,
        text="Test message",
        keyboard=None,
    )
    
    mock_bot.send_message.assert_called_once_with(
        chat_id=123456789,
        text="Test message",
    )
```

## Миграции Alembic

Модуль не имеет собственных миграций, так как не содержит моделей БД.

## Дополнительные материалы

- [aiogram документация](https://docs.aiogram.dev/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [docs/bus.md](../bus.md) — шина сообщений
