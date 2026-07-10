# Inter-Module HTTP Client Improvements

**Дата:** 2026-06-27
**Статус:** Approved

---

## Цель

1. Вынести базовые URL internal API в настройки (settings)
2. Создать отдельный http_client модуль в notifications для межмодульного взаимодействия
3. Унифицировать подход к HTTP-вызовам между модулями

---

## Задачи

### Task 1: Добавить INTERNAL_API_BASE_URL в settings

**Файл:** `src/core/config.py`

```python
# Internal API (межмодульное взаимодействие)
INTERNAL_API_BASE_URL: str = "http://localhost:8000/internal"
```

**Обоснование:**
- Единая точка конфигурации для всех internal API вызовов
- При выносе модулей в микросервисы — менять только в одном месте
- Упрощение тестирования (можно подменить URL)

---

### Task 2: Обновить telegram_clients/http_client.py

**Файл:** `src/modules/telegram_clients/http_client.py`

**Изменения:**
- Использовать `settings.INTERNAL_API_BASE_URL` вместо хардкода
- Обновить URL формирования:
  - `f"{settings.INTERNAL_API_BASE_URL}/media/"` вместо `f"http://localhost:{settings.PORT}/internal/media/"`
  - `f"{settings.INTERNAL_API_BASE_URL}/users/"` вместо `f"http://localhost:{settings.PORT}/internal/users/"`

---

### Task 3: Создать notifications/http_client.py

**Файл:** `src/modules/notifications/http_client.py`

```python
"""
HTTP-клиент для межмодульного взаимодействия.

Вызовы к другим модулям через internal API (httpx).
Не импортировать сервисы других модулей напрямую!
"""

import logging
import uuid

import httpx

from src.core.config import settings

logger = logging.getLogger(__name__)


async def resolve_user_by_auth_id(auth_id: uuid.UUID) -> str | None:
    """
    Резолвит email по auth_id через внутренний роут users.

    GET /internal/users/?filters=auth_id+eq+...
    Доступ ограничен network-level.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.INTERNAL_API_BASE_URL}/users/",
                params={"filters": f"auth_id+eq+{auth_id}"},
                timeout=5.0,
            )
            if response.status_code == 200:
                users = response.json()
                if users and len(users) > 0:
                    return users[0].get("email")
    except Exception:
        logger.exception("Ошибка резолва email для auth_id=%s", auth_id)
    return None
```

**Тесты:** `tests/modules/notifications/test_http_client.py`

```python
import pytest
import respx

from src.core.config import settings
from src.modules.notifications.http_client import resolve_user_by_auth_id


@respx.mock
async def test_resolve_user_by_auth_id_found():
    """GET /internal/users/ находит пользователя."""
    auth_id = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
    respx.get(f"{settings.INTERNAL_API_BASE_URL}/users/").mock(
        return_value=[{
            "id": "user-uuid",
            "auth_id": auth_id,
            "email": "user@example.com",
        }]
    )

    email = await resolve_user_by_auth_id(auth_id)
    assert email == "user@example.com"


@respx.mock
async def test_resolve_user_by_auth_id_not_found():
    """GET /internal/users/ не находит пользователя."""
    auth_id = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
    respx.get(f"{settings.INTERNAL_API_BASE_URL}/users/").mock(
        return_value=[]
    )

    email = await resolve_user_by_auth_id(auth_id)
    assert email is None
```

---

### Task 4: Обновить notification service для использования http_client

**Файл:** `src/modules/notifications/service.py`

**Изменения:**
- Добавить импорт: `from src.modules.notifications.http_client import resolve_user_by_auth_id`
- Обновить `send_notification()` для автоматического резолва email если не предоставлен recipient

```python
async def send_notification(
    self,
    session: AsyncSession,
    auth_id: uuid.UUID,
    template_name: str,
    channel: str,
    body: dict,
    recipient: str | None = None,  # Сделать опциональным
) -> NotificationLog:
    """
    Отправить уведомление.

    1. Найти шаблон (БД → файлы)
    2. Рендерить Jinja2
    3. Резолвить recipient если не предоставлен
    4. Отправить через провайдер
    5. Сохранить в лог
    """
    # Резолвим recipient если не предоставлен (для email)
    if recipient is None and channel == "email":
        recipient = await resolve_user_by_auth_id(auth_id)
        if recipient is None:
            # Лог с ошибкой
            log = await self.log_repo.create(session, {
                "auth_id": auth_id,
                "channel": channel,
                "template_name": template_name,
                "recipient": "",
                "subject": template_name,
                "body": "",
                "status": "failed",
                "error_message": "Не удалось резолвить email для auth_id",
            })
            return log

    if recipient is None:
        raise ValueError("recipient required for this channel")

    # ... остальной код
```

---

### Task 5: Обновить документацию

**Файл:** `docs/architecture.md` — секция "Межмодульное взаимодействие"

Добавить пример для notifications:

```python
# Пример: notifications резолвит email через users модуль
from src.modules.notifications.http_client import resolve_user_by_auth_id

email = await resolve_user_by_auth_id(auth_id)
# GET /internal/users/?filters=auth_id+eq+...
```

---

## Преимущества

1. **Единая конфигурация** — `INTERNAL_API_BASE_URL` в одном месте
2. **Изоляция модулей** — каждый модуль имеет свой http_client
3. **Легкое тестирование** — моки через respx
4. **Готовность к микросервисам** — при выносе меняется только URL в settings
5. **DRY** — общая логика в http_client, не в сервисах

---

## Чеклист реализации

- [ ] Task 1: INTERNAL_API_BASE_URL в settings
- [ ] Task 2: Обновить telegram_clients/http_client.py
- [ ] Task 3: Создать notifications/http_client.py + тесты
- [ ] Task 4: Обновить notification service
- [ ] Task 5: Обновить документацию
- [ ] Запустить все тесты (146+)
- [ ] ruff check
