# Шина сообщений

## Обзор

Шина сообщений — механизм взаимодействия между модулями без прямых импортов. Модули публикуют события, другие модули подписываются на них.

### Интерфейс

Все реализации шины следуют протоколу `MessageBus` (`src/bus/interface.py`):

```python
class MessageBus(Protocol):
    def publish(self, topic: str, message: dict) -> None: ...
    def subscribe(self, topic: str) -> Callable: ...
    def get_subscribers(self) -> dict[str, list[Callable]]: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
```

### Реализации

| Реализация | Когда использовать | Описание |
|------------|-------------------|----------|
| `InMemoryProducer` + `InMemoryConsumer` | Монолит (по умолчанию) | Обработчики вызываются в том же процессе |
| `KafkaProducerBus` + `KafkaConsumerRouter` | Микросервисы | Сообщения через Kafka-брокер |

Переключение — одна переменная в `.env`:

```env
MESSAGE_BUS=in_memory    # или kafka
```

---

## Реестр топиков

Все топики определены в `src/core/bus_topics.py` — **единственная точка истины**. Хардкод строк в коде запрещён.

| Константа | Топик | Модуль-источник | Описание |
|-----------|-------|-----------------|----------|
| `BusTopics.USER_REGISTERED` | `user.registered` | auth | Пользователь зарегистрирован |
| `BusTopics.USER_LOGGED_IN` | `user.logged_in` | auth | Пользователь авторизовался |
| `BusTopics.PROFILE_CREATED` | `profile.created` | users | Профиль создан |
| `BusTopics.PROFILE_UPDATED` | `profile.updated` | users | Профиль обновлён |
| `BusTopics.PROFILE_DELETED` | `profile.deleted` | users | Профиль удалён |
| `BusTopics.TG_MESSAGE_RECEIVED` | `tg.message.received` | telegram_clients | Входящее сообщение из Telegram |
| `BusTopics.TG_MESSAGE_SEND` | `tg.message.send` | telegram_clients | Отправить сообщение через аккаунт |
| `BusTopics.TG_ACCOUNT_CONNECTED` | `tg.account.connected` | telegram_clients | Аккаунт подключён |
| `BusTopics.TG_ACCOUNT_DISCONNECTED` | `tg.account.disconnected` | telegram_clients | Аккаунт отключён |
| `BusTopics.NOTIFICATION_SEND` | `notification.send` | notifications | Отправить уведомление |
| `BusTopics.MEDIA_UPLOADED` | `media.uploaded` | media | Файл загружен |
| `BusTopics.MEDIA_DELETED` | `media.deleted` | media | Файл удалён |

---

## События

Все события наследуются от `BaseEvent` (`src/bus/schemes.py`), который предоставляет:

- `timestamp` — автоматическая дата/время в UTC
- `to_bus_dict()` — сериализация через `model_dump(mode="json")` с добавлением `event_name`

### UserRegistered

Топик: `user.registered`
Источник: `AuthService.register()`

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"user.registered"` |
| auth_id | UUID | ID учётной записи |
| email | str | Email пользователя |
| timestamp | datetime | Время события |

### UserLoggedIn

Топик: `user.logged_in`
Источник: `AuthService.login()`

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"user.logged_in"` |
| auth_id | UUID | ID учётной записи |
| email | str | Email пользователя |
| timestamp | datetime | Время события |

### UserDeleted

Топик: `user.deleted`
Источник: `AuthService.delete_account()`

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"user.deleted"` |
| auth_id | UUID | ID удалённой учётной записи |

### ProfileCreated

Топик: `profile.created`
Источник: `UserService.create_user_profile()`

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"profile.created"` |
| auth_id | UUID | ID учётной записи |
| profile_id | UUID | ID профиля |
| timestamp | datetime | Время события |

### ProfileUpdated

Топик: `profile.updated`
Источник: `UserService.update_profile()`

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"profile.updated"` |
| auth_id | UUID | ID учётной записи |
| profile_id | UUID | ID профиля |
| fields_updated | list[str] | Список изменённых полей |
| timestamp | datetime | Время события |

### ProfileDeleted

Топик: `profile.deleted`
Источник: `UserService.delete_profile()`

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"profile.deleted"` |
| auth_id | UUID | ID учётной записи |
| profile_id | UUID | ID профиля |
| timestamp | datetime | Время события |

### TgMessageReceived

Топик: `tg.message.received`
Источник: `TelegramClientManager` (обработчик `on_new_message`)

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"tg.message.received"` |
| account_id | UUID | ID Telegram-аккаунта |
| chat_id | int | ID чата |
| message_id | int | ID сообщения |
| sender_id | int \| null | ID отправителя |
| text | str \| null | Текст сообщения |
| media | list[dict] | Массив media: `[{"type": "photo", "id": "file_id"}]` |
| timestamp | datetime | Время события |

### TgMessageSend

Топик: `tg.message.send`
Источник: Внешние модули (подписка в handlers.py)

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"tg.message.send"` |
| account_id | UUID | ID Telegram-аккаунта |
| chat_id | int | ID чата |
| text | str | Текст сообщения |
| media | list[dict] | Зарезервировано на будущее |

### TgAccountConnected

Топик: `tg.account.connected`
Источник: `TelegramClientService.verify_code()`, `verify_password()`

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"tg.account.connected"` |
| account_id | UUID | ID Telegram-аккаунта |
| auth_id | UUID | ID пользователя |
| phone | str | Номер телефона |
| telegram_id | int \| null | ID в Telegram |
| timestamp | datetime | Время события |

### TgAccountDisconnected

Топик: `tg.account.disconnected`
Источник: `TelegramClientService.delete_account()`

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"tg.account.disconnected"` |
| account_id | UUID | ID Telegram-аккаунта |
| auth_id | UUID | ID пользователя |
| reason | str | Причина: `"manual"`, `"error"`, `"deleted"` |
| timestamp | datetime | Время события |

### NotificationSend

Топик: `notification.send`
Источник: Любой модуль (подписка в notifications/handlers.py)

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"notification.send"` |
| auth_id | UUID | ID пользователя (для резолва email) |
| template_name | str | Имя Jinja2-шаблона |
| channel | str | Канал: `email` (default), `sms` (зарезервировано) |
| body | dict | Переменные для подстановки в шаблон |

### MediaUploaded

Топик: `media.uploaded`
Источник: `MediaService.upload()`

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"media.uploaded"` |
| file_id | UUID | ID загруженного файла |
| filename | str | Оригинальное имя файла |
| content_type | str | MIME-тип |
| size_bytes | int | Размер в байтах |
| is_public | bool | Публичный доступ |
| timestamp | datetime | Время события |

### MediaDeleted

Топик: `media.deleted`
Источник: `MediaService.delete()`

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"media.deleted"` |
| file_id | UUID | ID удалённого файла |
| storage_key | str | Ключ в хранилище |
| timestamp | datetime | Время события |

---

## Диаграмма потоков

```
┌──────────┐                                                    ┌──────────┐
│   auth   │                                                    │  users   │
│  module  │                                                    │  module  │
├──────────┤                                                    ├──────────┤
│          │  publish(user.registered)                          │          │
│ register │ ──────────────────────────────────────────────────▶│ handler  │
│          │                                                    │          │
│          │  publish(user.logged_in)                           │          │
│  login   │ ──────────────────────────────────────────────────▶│ handler  │
│          │                                                    │          │
│          │                                                    │          │
│          │  subscribe(profile.created)                        │  create  │
│          │ ◀──────────────────────────────────────────────────│          │
│          │                                                    │          │
│          │  subscribe(profile.updated)                        │  update  │
│          │ ◀──────────────────────────────────────────────────│          │
│          │                                                    │          │
│          │  subscribe(profile.deleted)                        │  delete  │
│          │ ◀──────────────────────────────────────────────────│          │
└──────────┘                     MessageBus                     └──────────┘

┌──────────────────────┐                                        ┌──────────┐
│  telegram_clients    │                                        │  Любой   │
│  module              │                                        │  модуль  │
├──────────────────────┤                                        ├──────────┤
│                      │  publish(tg.message.received)          │          │
│  ClientManager       │ ─────────────────────────────────────▶│ handler  │
│  (on_new_message)    │                                        │          │
│                      │  publish(tg.account.connected)        │          │
│  Service             │ ─────────────────────────────────────▶│          │
│                      │                                        │          │
│                      │  publish(tg.account.disconnected)     │          │
│                      │ ─────────────────────────────────────▶│          │
│                      │                                        │          │
│                      │  subscribe(tg.message.send)           │  Любой   │
│  ClientManager       │ ◀─────────────────────────────────────│  модуль  │
│  (send_message)      │                                        │          │
└──────────────────────┘                 MessageBus             └──────────┘
```

---

## Как добавить новое событие

1. **Добавьте топик** в `src/core/bus_topics.py`:

```python
class BusTopics:
    # ...
    MY_EVENT: str = "my_module.my_event"
```

2. **Создайте схему события** в `src/modules/my_module/schemas/events.py`:

```python
from src.bus.schemes import BaseEvent
from src.core.bus_topics import BusTopics


class MyEvent(BaseEvent):
    event_name: str = BusTopics.MY_EVENT
    entity_id: uuid.UUID
```

3. **Публикуйте из сервиса**:

```python
event = MyEvent(entity_id=entity.id)
self.message_bus.publish(BusTopics.MY_EVENT, event.to_bus_dict())
```

4. **Подпишите обработчик** в `handlers.py`:

```python
@bus.subscribe(BusTopics.MY_EVENT)
async def handle_my_event(message: dict) -> None:
    logger.info("Событие: %s", message.get("entity_id"))
```
