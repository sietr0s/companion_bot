# Шина сообщений

## Обзор

Шина сообщений — механизм взаимодействия между модулями без прямых импортов. Модули публикуют события, другие модули подписываются на них.

### Типы топиков

В проекте используется двухуровневое именование топиков:

| Тип | Суффикс | Кто публикует | Семантика |
|-----|---------|---------------|-----------|
| **Event** | `.event.` | **Владелец** модуля (в его домене что-то произошло) | Факт, который другие модули могут слушать |
| **Command** | `.command.` | **Не владелец** (другой модуль просит что-то сделать) | Запрос на side-effect (отправить сообщение, классифицировать и т.д.) |

**Пример:**

```
auth.event.user.registered      → Auth сообщает: "пользователь зарегистрировался"
telegram_clients.command.send_message → JobMatcher просит: "отправь сообщение через Telegram"
```

### Интерфейс

Публикация и потребление разделены на два протокола (`src/bus/interface.py`):

```python
class MessageProducer(Protocol):
    async def publish(self, topic: str, message: dict) -> None: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...


class MessageConsumer(Protocol):
    def subscribe(self, topic: str) -> Callable: ...
    def get_subscribers(self) -> dict[str, list[Callable]]: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
```

Producer только отправляет сообщения. Consumer владеет подписками, слушает
транспорт и вызывает обработчики. В in-memory режиме их связывает общая
`InMemoryTransport` с `asyncio.Queue`.

### Реализации

| Реализация | Когда использовать | Описание |
|------------|-------------------|----------|
| `InMemoryProducer` + `InMemoryConsumer` | Монолит (по умолчанию) | Обработчики вызываются в том же процессе |
| `KafkaProducerBus` + `KafkaConsumerRouter` | Микросервисы | Сообщения через Kafka-брокер |

При разрыве соединения `KafkaConsumerRouter` закрывает неисправный consumer,
создаёт новый с теми же топиками и повторяет подключение с exponential backoff.

Переключение — одна переменная в `.env`:

```env
MESSAGE_BUS=in_memory    # или kafka
```

---

## Реестр топиков

Все топики определены в `src/core/bus_topics.py` — **единственная точка истины**. Хардкод строк в коде запрещён.

### Events (публикует владелец модуля)

| Константа | Топик | Модуль-источник | Описание |
|-----------|-------|-----------------|----------|
| `BusTopics.USER_REGISTERED` | `auth.event.user.registered` | auth | Пользователь зарегистрирован |
| `BusTopics.USER_LOGGED_IN` | `auth.event.user.logged_in` | auth | Пользователь авторизовался |
| `BusTopics.USER_DELETED` | `auth.event.user.deleted` | auth | Учётная запись удалена |
| `BusTopics.PROFILE_CREATED` | `users.event.profile.created` | users | Профиль создан |
| `BusTopics.PROFILE_UPDATED` | `users.event.profile.updated` | users | Профиль обновлён |
| `BusTopics.PROFILE_DELETED` | `users.event.profile.deleted` | users | Профиль удалён |
| `BusTopics.TG_MESSAGE_RECEIVED` | `telegram_clients.event.message.received` | telegram_clients | Входящее сообщение из Telegram |
| `BusTopics.TG_ACCOUNT_CONNECTED` | `telegram_clients.event.account.connected` | telegram_clients | Аккаунт подключён |
| `BusTopics.TG_ACCOUNT_DISCONNECTED` | `telegram_clients.event.account.disconnected` | telegram_clients | Аккаунт отключён |
| `BusTopics.MEDIA_UPLOADED` | `media.event.uploaded` | media | Файл загружен |
| `BusTopics.MEDIA_DELETED` | `media.event.deleted` | media | Файл удалён |
| `BusTopics.BOT_MESSAGE_INCOMING` | `job_bot.event.message.incoming` | job_bot | Входящее сообщение от пользователя |
| `BusTopics.JOB_OFFER_PARSED` | `job_matcher.event.offer.parsed` | job_matcher | Вакансия распарсена |
| `BusTopics.JOB_OFFER_CLASSIFIED` | `job_matcher.event.offer.classified` | job_matcher | Вакансия классифицирована |
| `BusTopics.SUBSCRIPTION_CREATED` | `job_matcher.event.subscription.created` | job_matcher | Подписка создана |
| `BusTopics.SUBSCRIPTION_UPDATED` | `job_matcher.event.subscription.updated` | job_matcher | Подписка обновлена |
| `BusTopics.SUBSCRIPTION_DELETED` | `job_matcher.event.subscription.deleted` | job_matcher | Подписка удалена |
| `BusTopics.TEXT_CLASSIFY_COMPLETED` | `classifier.event.classify.completed` | classifier | Классификация завершена |

#### BotMessageIncoming

Топик: `job_bot.event.message.incoming`. Источник: `job_bot`.

| Поле | Тип | Описание |
|------|-----|----------|
| `chat_id` | int | ID чата, куда бот отправляет ответ |
| `text` | str | Текст входящего сообщения |
| `command` | str \| null | Команда без суффикса имени бота, например `/start` |
| `callback_data` | str \| null | Данные нажатой inline-кнопки |
| `message_id` | int \| null | ID сообщения с inline-клавиатурой; заполняется для callback |
| `user.telegram_id` | int | Обязательный ID автора в Telegram; используется как идентификатор Auth |
| `user.username` | str \| null | Username автора |
| `user.first_name` | str | Имя автора |
| `user.last_name` | str \| null | Фамилия автора |

`chat_id` и `user.telegram_id` имеют разное назначение и могут различаться в групповых чатах.
Событие без объекта `user` не соответствует контракту и не обрабатывается.

### Commands (публикует НЕ владелец)

| Константа | Топик | Модуль-источник | Описание |
|-----------|-------|-----------------|----------|
| `BusTopics.TG_MESSAGE_SEND` | `telegram_clients.command.send_message` | **любой** модуль | Отправить сообщение через Telegram-аккаунт |
| `BusTopics.NOTIFICATION_SEND` | `notifications.command.send` | **любой** модуль | Отправить уведомление |
| `BusTopics.TEXT_CLASSIFY_REQUEST` | `classifier.command.classify` | **любой** модуль | Запросить классификацию текста |
| `BusTopics.BOT_MESSAGE_OUTGOING` | `job_bot.command.send_message` | **любой** модуль | Отправить сообщение пользователю через бота |
| `BusTopics.BOT_MESSAGE_EDIT` | `job_bot.command.edit_message` | **любой** модуль | Заменить текст и клавиатуру сообщения бота |

---

## События

Все события наследуются от `BaseEvent` (`src/bus/schemes.py`), который предоставляет:

- `timestamp` — автоматическая дата/время в UTC
- `to_bus_dict()` — сериализация через `model_dump(mode="json")` с добавлением `event_name`

### UserRegistered

Топик: `auth.event.user.registered`
Источник: `AuthService.register()`

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"auth.event.user.registered"` |
| auth_id | UUID | ID учётной записи |
| email | str | Email пользователя |
| timestamp | datetime | Время события |

### UserLoggedIn

Топик: `auth.event.user.logged_in`
Источник: `AuthService.login()`

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"auth.event.user.logged_in"` |
| auth_id | UUID | ID учётной записи |
| email | str | Email пользователя |
| timestamp | datetime | Время события |

### UserDeleted

Топик: `auth.event.user.deleted`
Источник: `AuthService.delete_account()`

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"auth.event.user.deleted"` |
| auth_id | UUID | ID удалённой учётной записи |

### ProfileCreated

Топик: `users.event.profile.created`
Источник: `UserService.create_user_profile()`

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"users.event.profile.created"` |
| auth_id | UUID | ID учётной записи |
| profile_id | UUID | ID профиля |
| timestamp | datetime | Время события |

### ProfileUpdated

Топик: `users.event.profile.updated`
Источник: `UserService.update_profile()`

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"users.event.profile.updated"` |
| auth_id | UUID | ID учётной записи |
| profile_id | UUID | ID профиля |
| fields_updated | list[str] | Список изменённых полей |
| timestamp | datetime | Время события |

### ProfileDeleted

Топик: `users.event.profile.deleted`
Источник: `UserService.delete_profile()`

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"users.event.profile.deleted"` |
| auth_id | UUID | ID учётной записи |
| profile_id | UUID | ID профиля |
| timestamp | datetime | Время события |

### TgMessageReceived

Топик: `telegram_clients.event.message.received`
Источник: `TelegramClientManager` (обработчик `on_new_message`)

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"telegram_clients.event.message.received"` |
| account_id | UUID | ID Telegram-аккаунта |
| chat_id | int | ID чата |
| message_id | int | ID сообщения |
| sender | object | Автор сообщения: `sender_id`, `username`, `first_name`, `last_name` |
| text | str \| null | Текст сообщения |
| media | list[dict] | Массив media: `[{"type": "photo", "id": "file_id"}]` |
| timestamp | datetime | Время события |

Пример `sender`:

```json
{
  "sender_id": 123456789,
  "username": "vacancy_author",
  "first_name": "Иван",
  "last_name": "Иванов"
}
```

### TgMessageSend

Топик: `telegram_clients.command.send_message`
Источник: Внешние модули (подписка в handlers.py)

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"telegram_clients.command.send_message"` |
| account_id | UUID | ID Telegram-аккаунта |
| chat_id | int | ID чата |
| text | str | Текст сообщения |
| media | list[dict] | Зарезервировано на будущее |

### TgAccountConnected

Топик: `telegram_clients.event.account.connected`
Источник: `TelegramClientService.verify_code()`, `verify_password()`

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"telegram_clients.event.account.connected"` |
| account_id | UUID | ID Telegram-аккаунта |
| auth_id | UUID | ID пользователя |
| phone | str | Номер телефона |
| telegram_id | int \| null | ID в Telegram |
| timestamp | datetime | Время события |

### TgAccountDisconnected

Топик: `telegram_clients.event.account.disconnected`
Источник: `TelegramClientService.delete_account()`

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"telegram_clients.event.account.disconnected"` |
| account_id | UUID | ID Telegram-аккаунта |
| auth_id | UUID | ID пользователя |
| reason | str | Причина: `"manual"`, `"error"`, `"deleted"` |
| timestamp | datetime | Время события |

### NotificationSend

Топик: `notifications.command.send`
Источник: Любой модуль (подписка в notifications/handlers.py)

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"notifications.command.send"` |
| auth_id | UUID | ID пользователя для резолва email или Telegram chat ID |
| template_name | str | Имя Jinja2-шаблона |
| channel | str | Канал: `email` (default), `telegram`; `sms` зарезервирован |
| body | dict | Переменные для подстановки в шаблон |

### MediaUploaded

Топик: `media.event.uploaded`
Источник: `MediaService.upload()`

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"media.event.uploaded"` |
| file_id | UUID | ID загруженного файла |
| filename | str | Оригинальное имя файла |
| content_type | str | MIME-тип |
| size_bytes | int | Размер в байтах |
| is_public | bool | Публичный доступ |
| timestamp | datetime | Время события |

### MediaDeleted

Топик: `media.event.deleted`
Источник: `MediaService.delete()`

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"media.event.deleted"` |
| file_id | UUID | ID удалённого файла |
| storage_key | str | Ключ в хранилище |
| timestamp | datetime | Время события |

---

## Диаграмма потоков

```
┌──────────┐              ┌──────────┐
│   auth   │              │  users   │
│  module  │              │  module  │
├──────────┤              ├──────────┤
│          │  event       │          │
│ register │─────────────▶│ handler  │
│          │              │          │
│          │  event       │          │
│  login   │─────────────▶│ handler  │
│          │              │          │
│          │              │          │
│          │  event       │          │
│          │◀─────────────│  create  │
│          │              │          │
│          │  event       │          │
│          │◀─────────────│  update  │
│          │              │          │
│          │  event       │          │
│          │◀─────────────│  delete  │
└──────────┘ Producer/Consumer └──────────┘

┌──────────────────────┐     ┌──────────┐
│  telegram_clients    │     │  Любой   │
│  module              │     │  модуль  │
├──────────────────────┤     ├──────────┤
│                      │event │          │
│  ClientManager       │─────▶│ handler  │
│  (on_new_message)    │     │          │
│                      │     │          │
│  Service             │event │          │
│                      │─────▶│          │
│                      │     │          │
│                      │event │          │
│                      │─────▶│          │
│                      │     │          │
│                      │command│          │
│  ClientManager       │◀────│  модуль  │
│  (send_message)      │     │          │
└──────────────────────┘     └──────────┘
```

---

## Как добавить новое событие

1. **Определите тип** — event или command:
   - Если модуль сообщает о том, что произошло в его домене → **event**
   - Если другой модуль просит что-то сделать → **command**

2. **Добавьте топик** в `src/core/bus_topics.py`:

```python
class BusTopics:
    # Для события:
    MY_EVENT: str = "my_module.event.something_happened"
    # Для команды:
    MY_COMMAND: str = "my_module.command.do_something"
```

3. **Создайте схему события** в `src/modules/my_module/schemas/events.py`:

```python
from src.bus.schemes import BaseEvent
from src.core.bus_topics import BusTopics


class MyEvent(BaseEvent):
    event_name: str = BusTopics.MY_EVENT
    entity_id: uuid.UUID
```

4. **Публикуйте из сервиса**:

```python
event = MyEvent(entity_id=entity.id)
await self.message_bus.publish(BusTopics.MY_EVENT, event.to_bus_dict())
```

5. **Подпишите обработчик** в `handlers.py`:

```python
from src.bus import get_consumer

consumer = get_consumer()


@consumer.subscribe(BusTopics.MY_EVENT)
async def handle_my_event(message: dict) -> None:
    logger.info("Событие: %s", message.get("entity_id"))
```
