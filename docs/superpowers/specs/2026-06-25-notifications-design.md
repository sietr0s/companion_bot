# Модуль notifications — Design Spec

**Дата:** 2026-06-25
**Статус:** Approved

## Цель

Модуль нотификаций: отправка email (и SMS в будущем) по событиям из шины. Шаблоны — Jinja2 (файлы + БД). Любой модуль может опубликовать событие `notification.send` — notifications обработает и отправит.

## Решения

| Решение | Выбор | Обоснование |
|---------|-------|-------------|
| Email провайдер | Абстракция + SMTP | Гибкость, можно подставить любой API |
| Шаблоны | Файлы + БД | Файлы как дефолт, БД для переопределения |
| Разрешение email | Внутренний роут /internal/users/ | Изоляция модулей, network-level доступ |
| История | Хранить в БД | Отладка, аналитика, показ пользователю |
| Архитектура | Подписка на шину | Event-driven, любой модуль может отправить |
| Внутренние роуты | /internal/ prefix, без авторизации | Доступ ограничен network-level (Docker, k8s) |

---

## Модели БД

### notification_template

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| id | UUID | PK, default=uuid4 | Идентификатор |
| name | VARCHAR(100) | UNIQUE, NOT NULL | Имя шаблона (`welcome`, `password_reset`) |
| channel | VARCHAR(20) | NOT NULL | Канал: `email`, `sms` (зарезервировано) |
| subject_template | TEXT | NULLABLE | Jinja2-шаблон темы (для email) |
| body_template | TEXT | NOT NULL | Jinja2-шаблон тела |
| is_active | BOOLEAN | DEFAULT TRUE | Включён ли шаблон |
| created_at | TIMESTAMP | NOT NULL | Авто |
| updated_at | TIMESTAMP | NOT NULL | Авто |

### notification_log

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| id | UUID | PK, default=uuid4 | Идентификатор |
| auth_id | UUID | NOT NULL, INDEX | ID пользователя (без FK) |
| channel | VARCHAR(20) | NOT NULL | `email`, `sms` |
| template_name | VARCHAR(100) | NOT NULL | Имя использованного шаблона |
| recipient | VARCHAR(255) | NOT NULL | Email/телефон получателя |
| subject | TEXT | NULLABLE | Отрендеренная тема |
| body | TEXT | NOT NULL | Отрендеренное тело |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'pending' | `pending`, `sent`, `failed` |
| error_message | TEXT | NULLABLE | Ошибка (если failed) |
| created_at | TIMESTAMP | NOT NULL | Авто |
| updated_at | TIMESTAMP | NOT NULL | Авто |

---

## Структура модуля

```
src/modules/notifications/
├── __init__.py
├── models.py              # NotificationTemplate, NotificationLog
├── schemas/
│   ├── __init__.py
│   ├── api.py             # TemplateCreate, TemplateRead, TemplateUpdate, NotificationLogRead
│   └── events.py          # NotificationSend
├── repository.py          # NotificationTemplateRepository, NotificationLogRepository
├── providers/
│   ├── __init__.py
│   ├── base.py            # NotificationProvider (Protocol)
│   └── smtp.py            # SmtpProvider (aiosmtplib)
├── template_engine.py     # Jinja2 рендеринг (БД → файлы)
├── service.py             # NotificationService
├── handlers.py            # Подписка на notification.send
└── router.py              # CRUD шаблонов, история
```

---

## Шина сообщений

### Топик

| Константа | Топик | Направление | Описание |
|-----------|-------|-------------|----------|
| `NOTIFICATION_SEND` | `notification.send` | In (subscribe) | Отправить уведомление |

### Событие: NotificationSend

```json
{
  "event_name": "notification.send",
  "auth_id": "uuid",
  "template_name": "welcome",
  "channel": "email",
  "body": {
    "first_name": "Иван",
    "confirmation_link": "https://..."
  }
}
```

- `auth_id` — для резолва email через внутренний роут
- `template_name` — имя Jinja2-шаблона
- `channel` — `email` (в будущем `sms`)
- `body` — переменные для подстановки в шаблон

---

## API-роуты

### Шаблоны (CRUD)

| Метод | Путь | Описание | Ответ |
|-------|------|----------|-------|
| POST | `/notifications/templates/` | Создать шаблон | TemplateRead (201) |
| GET | `/notifications/templates/` | Список шаблонов | list[TemplateRead] |
| GET | `/notifications/templates/{id}` | Получить по ID | TemplateRead |
| PATCH | `/notifications/templates/{id}` | Обновить шаблон | TemplateRead |
| DELETE | `/notifications/templates/{id}` | Удалить шаблон | 204 |

### История

| Метод | Путь | Описание | Ответ |
|-------|------|----------|-------|
| GET | `/notifications/history/` | История уведомлений | list[NotificationLogRead] |

> History возвращает уведомления текущего пользователя (по JWT). Templates — для администраторов (в будущем).

### Внутренний роут (users)

| Метод | Путь | Описание | Ответ |
|-------|------|----------|-------|
| GET | `/internal/users/` | Получить пользователей с фильтрацией | list[UserRead] |

Query params: `filters=field+operator+value` — универсальная фильтрация.

**Синтаксис фильтров:**

```
GET /internal/users/?filters=auth_id+eq+550e8400-...
GET /internal/users/?filters=email+eq+test@test.com
GET /internal/users/?filters=first_name+ilike+Иван
GET /internal/users/?filters=auth_id+eq+...&filters=email+eq+...
```

Формат: `field+operator+value`, где `+` — разделитель.

**Поддерживаемые операторы:**

| Оператор | Описание | Пример |
|----------|----------|--------|
| `eq` | Равно | `email+eq+test@test.com` |
| `ne` | Не равно | `status+ne+deleted` |
| `gt` | Больше | `age+gt+18` |
| `ge` | Больше или равно | `age+ge+18` |
| `lt` | Меньше | `age+lt+65` |
| `le` | Меньше или равно | `age+le+65` |
| `like` | LIKE (чувствительный) | `name+like+%test%` |
| `ilike` | ILIKE (нечувствительный) | `name+ilike+%ivan%` |
| `in` | В списке (через запятую) | `status+in+active,pending` |

Доступ: network-level (Docker network, k8s NetworkPolicy), без JWT.

---

## Провайдеры уведомлений

### NotificationProvider (Protocol)

```python
class NotificationProvider(Protocol):
    async def send(self, to: str, subject: str, body: str) -> None: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
```

### SmtpProvider

Реализация через `aiosmtplib`. Настройки из `.env`:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your@email.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true
SMTP_FROM_EMAIL=noreply@yourapp.com
SMTP_FROM_NAME=Your App
```

---

## Template Engine

### Поиск шаблона

1. **БД** — ищем `NotificationTemplate` по `name` и `channel`, где `is_active=True`
2. **Файлы** — если не найден в БД, ищем `templates/{channel}/{name}.j2`
3. **Ошибка** — если не найден нигде, логируем и сохраняем failed в notification_log

### Файловая структура шаблонов

```
templates/
├── email/
│   ├── welcome.j2
│   ├── password_reset.j2
│   └── profile_updated.j2
└── sms/
    └── verification_code.j2
```

### Рендеринг

```python
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader("templates/"))
template = env.get_template(f"{channel}/{name}.j2")
rendered = template.render(**body)
```

Шаблон из БД:

```python
from jinja2 import Template
template = Template(db_template.body_template)
rendered = template.render(**body)
```

---

## Обработчик отправки (handlers.py)

```python
@bus.subscribe(BusTopics.NOTIFICATION_SEND)
async def handle_notification_send(message: dict):
    auth_id = message.get("auth_id")
    template_name = message.get("template_name")
    channel = message.get("channel", "email")
    body = message.get("body", {})

    # 1. Резолвим email через внутренний роут
    user = await internal_get_user(auth_id)
    if not user or not user.get("email"):
        logger.warning("Email не найден для auth_id=%s", auth_id)
        return

    # 2. Ищем шаблон (БД → файлы)
    template = await find_template(template_name, channel)

    # 3. Рендерим
    subject, rendered_body = render_template(template, body)

    # 4. Отправляем
    await provider.send(user["email"], subject, rendered_body)

    # 5. Сохраняем в историю
    await save_log(auth_id, channel, template_name, user["email"], subject, rendered_body, "sent")
```

---

## Расширение BaseRepository

Добавить метод `get_list()` с парсингом фильтров `field+operator+value`:

```python
from enum import StrEnum

class FilterOperator(StrEnum):
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GE = "ge"
    LT = "lt"
    LE = "le"
    LIKE = "like"
    ILIKE = "ilike"
    IN = "in"

class Filter(BaseModel):
    field: str
    operator: FilterOperator
    value: str

def parse_filters(raw: list[str]) -> list[Filter]:
    """Парсит 'field+op+value' → Filter."""
    filters = []
    for item in raw:
        parts = item.split("+", 2)
        if len(parts) == 3:
            filters.append(Filter(field=parts[0], operator=parts[1], value=parts[2]))
    return filters

async def get_list(
    self,
    session: AsyncSession,
    filters: list[Filter] | None = None,
    skip: int = 0,
    limit: int = 100,
) -> Sequence[ModelType]:
    """Получить список сущностей с фильтрацией."""
    stmt = select(self.model)
    if filters:
        for f in filters:
            if not hasattr(self.model, f.field):
                continue
            col = getattr(self.model, f.field)
            match f.operator:
                case FilterOperator.EQ: stmt = stmt.where(col == f.value)
                case FilterOperator.NE: stmt = stmt.where(col != f.value)
                case FilterOperator.GT: stmt = stmt.where(col > f.value)
                case FilterOperator.GE: stmt = stmt.where(col >= f.value)
                case FilterOperator.LT: stmt = stmt.where(col < f.value)
                case FilterOperator.LE: stmt = stmt.where(col <= f.value)
                case FilterOperator.LIKE: stmt = stmt.where(col.like(f.value))
                case FilterOperator.ILIKE: stmt = stmt.where(col.ilike(f.value))
                case FilterOperator.IN: stmt = stmt.where(col.in_(f.value.split(",")))
    stmt = stmt.offset(skip).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()
```

---

## Конфигурация

Добавить в `Settings` (`core/config.py`):

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `SMTP_HOST` | `localhost` | SMTP сервер |
| `SMTP_PORT` | `587` | Порт SMTP |
| `SMTP_USERNAME` | — | Логин SMTP |
| `SMTP_PASSWORD` | — | Пароль SMTP |
| `SMTP_USE_TLS` | `true` | Использовать TLS |
| `SMTP_FROM_EMAIL` | `noreply@example.com` | Email отправителя |
| `SMTP_FROM_NAME` | `App` | Имя отправителя |
| `TEMPLATES_DIR` | `templates` | Директория файловых шаблонов |

---

## Зависимости

Добавить в `requirements.txt`:
- `aiosmtplib>=3.0.0`
- `jinja2>=3.1.0`
- `httpx>=0.27.0`

---

## Интеграция с существующим проектом

1. Добавить топик `NOTIFICATION_SEND` в `BusTopics`
2. Добавить фабрики в `dependencies.py`
3. Подключить роутер в `main.py`
4. Зарегистрировать обработчики в `main.py`
5. Добавить внутренний роут `/internal/users/` в модуль users
6. Расширить `BaseRepository` методом `get_list()`
7. Добавить зависимости в `requirements.txt`
