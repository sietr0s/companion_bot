# Правила изоляции модулей

## Зачем нужна изоляция

Модульная изоляция — фундамент Modular Monolith. Она гарантирует, что:

1. Модули можно разрабатывать и тестировать независимо
2. Модуль можно вынести в микросервис без переписывания
3. Изменения в одном модуле не ломают другой
4. Команда может работать над модулем автономно

---

## ✅ Разрешено

| Действие | Пример |
|----------|--------|
| Импорт из `src.base.*` | `from src.base.model import BaseModel` |
| Импорт из `src.core.*` | `from src.core.config import settings` |
| Импорт из `src.bus.*` | `from src.bus.interface import MessageBus` |
| Импорт из собственного модуля | `from src.modules.auth.models import Auth` (внутри auth) |
| Публикация событий через шину | `self.message_bus.publish(BusTopics.USER_REGISTERED, ...)` |
| Подписка на события через шину | `@bus.subscribe(BusTopics.PROFILE_CREATED)` |
| Использование `Protocol` для интерфейсов | `class UserCreator(Protocol)` |
| Передача ID другого модуля как аргумент | `auth_id: uuid.UUID` из JWT |

---

## ❌ Запрещено

| Действие | Почему |
|----------|--------|
| Прямой импорт модели другого модуля | `from src.modules.auth.models import Auth` из users — **нельзя** |
| Прямой импорт сервиса другого модуля **из других модулей** | `from src.modules.auth.service import AuthService` из users — **нельзя** |
| Прямой импорт репозитория другого модуля **из других модулей** | Жёсткая связанность, невозможно вынести модуль |
| ForeignKey на таблицу другого модуля | Модули не могут жить в разных БД |
| Общие таблицы между модулями | Нарушает принцип единого владельца данных |
| Хардкод строк топиков | `"user.registered"` — опечатки, нет автодополнения |
| Передача auth_id в схеме Create | ID из другого модуля — аргумент метода, не поле формы |

### Исключение: core/clients

**Важно:** Модуль `src/core/clients/` **разрешает** прямые импорты сервисов модулей. Это единственное исключение из правила изоляции.

**Почему это исключение:**

1. **Монолитная архитектура** — все модули в одном процессе, HTTP не нужен
2. **План миграции** — при выносе в микросервисы клиенты будут переписаны на HTTP
3. **Удобство** — не нужно дублировать код HTTP-клиентов в каждом модуле

**Пример:**
```python
# ✅ Разрешено: src/core/clients/users_client.py
from src.modules.users.service import UserService
from src.modules.users.repository import UserRepository

class UsersClient:
    async def resolve_email_by_auth_id(self, auth_id: UUID) -> str | None:
        # Прямой вызов сервиса
```

**Запрещено в других модулях:**
```python
# ❌ Запрещено: src/modules/notifications/service.py
from src.modules.users.service import UserService  # Нельзя напрямую!

# ✅ Правильно: использовать Clients
from src.core.clients import UsersClient
```

---

## Как модули общаются

### Паттерн: Event-Driven Architecture

```
┌─────────────┐    publish("user.registered")    ┌─────────────┐
│    auth      │ ───────────────────────────────▶ │    users     │
│   module     │                                  │   module     │
│             │ ◀───────────────────────────────── │             │
└─────────────┘    subscribe("profile.updated")   └─────────────┘
                         MessageBus
```

1. **Модуль A** публикует событие в шину через `message_bus.publish()`
2. **Модуль B** подписан на топик через `@bus.subscribe()`
3. Ни один модуль не знает о внутреннем устройстве другого

### Паттерн: Protocol (интерфейс)

Если модулю нужно вызвать метод другого модуля напрямую:

```python
# Используем клиенты из src/core/clients/
from src.core.clients.users_client import UsersClient

client = UsersClient()
email = await client.resolve_email_by_auth_id(auth_id)
```

Клиенты находятся в `src/core/clients/` и используют прямые импорты сервисов модулей — это **единственное разрешённое исключение** из правил изоляции. При выносе модуля в микросервис клиент переписывается на HTTP.

---

## Правила для БД

### Один модуль — один владелец таблицы

Каждая таблица принадлежит ровно одному модулю. Только этот модуль:
- Читает из таблицы
- Пишет в таблицу
- Определяет схему и миграции

### Нет ForeignKey между модулями

```
❌ Плохо:
auth_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth.id"))

✅ Хорошо:
auth_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
```

Ссылочная целостность обеспечивается на уровне бизнес-логики, а не СУБД.

### Нет общих таблиц

Если двум модулям нужны одни и те же данные — они дублируются или передаются через события. Это цена изоляции.

---

## Правила для шины сообщений

### Топики — только из BusTopics

```python
❌ Плохо:
self.message_bus.publish("user.registered", data)

✅ Хорошо:
self.message_bus.publish(BusTopics.USER_REGISTERED, data)
```

### Обработчики — идемпотентные

Событие может быть доставлено повторно (особенно в Kafka). Обработчик должен быть безопасен при повторном вызове.

### Обработчики — без прямых импортов

```python
❌ Плохо:
from src.modules.auth.service import AuthService

@bus.subscribe(BusTopics.USER_REGISTERED)
async def handle(message):
    auth_service = AuthService(...)  # прямая связь!

✅ Хорошо:
@bus.subscribe(BusTopics.USER_REGISTERED)
async def handle(message):
    logger.info("Пользователь: %s", message.get("auth_id"))
```

---

## Визуальная проверка изоляции

Если в `src/modules/users/` есть импорт из `src/modules/auth/` (кроме Protocol) — **изоляция нарушена**.

Проверка одной командой:

```bash
# Должно вернуть пустой результат
grep -r "from src.modules.auth" src/modules/users/
grep -r "from src.modules.users" src/modules/auth/
```
