# Internal HTTP Clients Refactoring Plan

**Дата:** 2026-06-27
**Статус:** Draft

---

## Цель

Вынести общие HTTP-клиенты для межмодульного взаимодействия из модулей (`telegram_clients/`, `notifications/`) в общий модуль `src/core/clients/` для:
- Устранения дублирования кода
- Единой точки расширения для новых клиентов
- Упрощения тестирования и поддержки

---

## Проблема

Сейчас:
```
src/modules/telegram_clients/http_client.py  → resolve_user_by_auth_id()
src/modules/notifications/http_client.py     → resolve_user_by_auth_id()  ← ДУБЛЬ
```

**Проблемы:**
- Дублирование кода (одна и та же функция в двух местах)
- При изменении логики нужно менять в нескольких местах
- Каждый модуль создаёт свои копии клиентов

---

## Решение

Создать общий модуль `src/core/clients/` с переиспользуемыми клиентами:

```
src/core/clients/
├── __init__.py          # Экспорт всех клиентов
├── base.py              # Базовый класс с общей логикой
├── users_client.py      # UsersHTTPClient (resolve_user_by_auth_id)
└── media_client.py      # MediaHTTPClient (upload_media_to_storage)
```

---

## Архитектура

### Базовый класс (base.py)

```python
"""
Базовый класс для HTTP-клиентов межмодульного взаимодействия.

Общая логика:
- INTERNAL_API_BASE_URL из settings
- Таймауты
- Логирование ошибок
- Обработка статус-кодов
"""

import logging
from typing import Any

import httpx

from src.core.config import settings

logger = logging.getLogger(__name__)


class BaseHTTPClient:
    """Базовый класс для всех internal HTTP клиентов."""

    def __init__(self, base_url: str | None = None, timeout: float = 10.0) -> None:
        self._base_url = base_url or settings.INTERNAL_API_BASE_URL
        self._timeout = timeout

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response | None:
        """
        Выполнить HTTP-запрос с обработкой ошибок.

        Возвращает Response или None при ошибке.
        """
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self._base_url}{path}"
                response = await client.request(
                    method,
                    url,
                    timeout=self._timeout,
                    **kwargs,
                )
                return response
        except Exception:
            logger.exception("Ошибка HTTP-запроса: %s %s", method, path)
        return None

    async def get(self, path: str, **kwargs: Any) -> httpx.Response | None:
        """GET запрос."""
        return await self._request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> httpx.Response | None:
        """POST запрос."""
        return await self._request("POST", path, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> httpx.Response | None:
        """DELETE запрос."""
        return await self._request("DELETE", path, **kwargs)
```

### UsersHTTPClient (users_client.py)

```python
"""
HTTP-клиент для взаимодействия с users модулем.

Использование:
    from src.core.clients import UsersHTTPClient

    users_client = UsersHTTPClient()
    email = await users_client.resolve_user_by_auth_id(auth_id)
"""

import logging
import uuid

from src.core.clients.base import BaseHTTPClient

logger = logging.getLogger(__name__)


class UsersHTTPClient(BaseHTTPClient):
    """Клиент для вызовов к users модулю через internal API."""

    async def resolve_user_by_auth_id(
        self,
        auth_id: uuid.UUID,
    ) -> str | None:
        """
        Резолвит email по auth_id через GET /internal/users/.

        GET /internal/users/?filters=auth_id+eq+...

        Возвращает email или None если пользователь не найден.
        """
        response = await self.get(
            "/users/",
            params={"filters": f"auth_id+eq+{auth_id}"},
        )

        if response and response.status_code == 200:
            users = response.json()
            if users and len(users) > 0:
                return users[0].get("email")
        return None
```

### MediaHTTPClient (media_client.py)

```python
"""
HTTP-клиент для взаимодействия с media модулем.

Использование:
    from src.core.clients import MediaHTTPClient

    media_client = MediaHTTPClient()
    file_id = await media_client.upload_media_to_storage(...)
"""

import logging

from src.core.clients.base import BaseHTTPClient

logger = logging.getLogger(__name__)


class MediaHTTPClient(BaseHTTPClient):
    """Клиент для вызовов к media модулю через internal API."""

    async def upload_media_to_storage(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str,
        is_public: bool = False,
    ) -> str | None:
        """
        Загрузить медиа-файл в storage модуль.

        POST /internal/media/

        Возвращает file_id или None при ошибке.
        """
        files = {"file": (filename, file_bytes, content_type)}
        data = {"is_public": str(is_public).lower()}

        response = await self.post(
            "/media/",
            files=files,
            data=data,
        )

        if response and response.status_code == 201:
            return response.json()["id"]

        if response:
            logger.error(
                "Ошибка загрузки медиа в storage: %d %s",
                response.status_code,
                response.text[:200],
            )
        return None

    async def get_media_file(
        self,
        file_id: str,
    ) -> bytes | None:
        """
        Скачать файл из storage.

        GET /internal/media/{file_id}/download

        Возвращает bytes или None при ошибке.
        """
        response = await self.get(f"/media/{file_id}/download")

        if response and response.status_code == 200:
            return response.content
        return None

    async def delete_media_file(
        self,
        file_id: str,
    ) -> bool:
        """
        Удалить файл из storage.

        DELETE /internal/media/{file_id}

        Возвращает True если успешно.
        """
        response = await self.delete(f"/media/{file_id}")
        return bool(response and response.status_code == 204)
```

---

## План работ

### Task 1: Создать src/core/clients/

- [ ] **Step 1.1:** Создать `src/core/clients/__init__.py`
- [ ] **Step 1.2:** Создать `src/core/clients/base.py` с `BaseHTTPClient`
- [ ] **Step 1.3:** Создать `src/core/clients/users_client.py` с `UsersHTTPClient`
- [ ] **Step 1.4:** Создать `src/core/clients/media_client.py` с `MediaHTTPClient`
- [ ] **Step 1.5:** Обновить `src/core/clients/__init__.py` для экспорта

**Тесты:**
- [ ] **Step 1.6:** Создать `tests/core/clients/test_base_client.py`
- [ ] **Step 1.7:** Создать `tests/core/clients/test_users_client.py`
- [ ] **Step 1.8:** Создать `tests/core/clients/test_media_client.py`

---

### Task 2: Обновить telegram_clients

- [ ] **Step 2.1:** Заменить импорт в `client_manager.py`:
  ```python
  # Было:
  from src.modules.telegram_clients.http_client import upload_media_to_storage

  # Стало:
  from src.core.clients import MediaHTTPClient

  media_client = MediaHTTPClient()
  file_id = await media_client.upload_media_to_storage(...)
  ```

- [ ] **Step 2.2:** Удалить `src/modules/telegram_clients/http_client.py`
- [ ] **Step 2.3:** Удалить `tests/modules/telegram_clients/test_http_client.py`
- [ ] **Step 2.4:** Обновить тесты `test_client_manager_media.py`

---

### Task 3: Обновить notifications

- [ ] **Step 3.1:** Заменить импорт в `service.py`:
  ```python
  # Было:
  from src.modules.notifications.http_client import resolve_user_by_auth_id

  # Стало:
  from src.core.clients import UsersHTTPClient

  users_client = UsersHTTPClient()
  email = await users_client.resolve_user_by_auth_id(auth_id)
  ```

- [ ] **Step 3.2:** Удалить `src/modules/notifications/http_client.py`
- [ ] **Step 3.3:** Удалить `tests/modules/notifications/test_http_client.py`
- [ ] **Step 3.4:** Обновить тесты сервиса уведомлений

---

### Task 4: Обновить документацию

- [ ] **Step 4.1:** Обновить `docs/architecture.md` — секция "Межмодульное взаимодействие"
- [ ] **Step 4.2:** Обновить `docs/api.md` — примеры использования клиентов
- [ ] **Step 4.3:** Добавить документацию для `src/core/clients/`

---

### Task 5: Финальная проверка

- [ ] **Step 5.1:** Запустить все тесты: `pytest tests/ -v --tb=short`
- [ ] **Step 5.2:** Запустить linter: `ruff check src/ tests/ --fix`
- [ ] **Step 5.3:** Закоммитить все изменения

---

## Структура после рефакторинга

```
src/core/clients/
├── __init__.py              # from .users_client import UsersHTTPClient
│                            # from .media_client import MediaHTTPClient
├── base.py                  # BaseHTTPClient
├── users_client.py          # UsersHTTPClient
└── media_client.py          # MediaHTTPClient

src/modules/telegram_clients/
├── client_manager.py        # from src.core.clients import MediaHTTPClient
└── ...                      # http_client.py УДАЛЁН

src/modules/notifications/
├── service.py               # from src.core.clients import UsersHTTPClient
└── ...                      # http_client.py УДАЛЁН

tests/core/clients/
├── __init__.py
├── test_base_client.py
├── test_users_client.py
└── test_media_client.py

tests/modules/telegram_clients/
└── ...                      # test_http_client.py УДАЛЁН

tests/modules/notifications/
└── ...                      # test_http_client.py УДАЛЁН
```

---

## Преимущества

| До | После |
|----|-------|
| Дублирование кода в каждом модуле | Единая реализация в `src/core/clients/` |
| При изменении — править в N местах | Правим в одном месте |
| Каждый модуль создаёт своих клиентов | Общие переиспользуемые клиенты |
| Сложнее тестировать | Общие тесты для всех клиентов |
| Нет единого стандарта | Базовый класс с общей логикой |

---

## Миграция

**Обратная совместимость:** Не требуется — меняем только internal API вызовы.

**Риск:** Низкий — все изменения покрыты тестами.

---

## Чеклист

- [ ] Task 1: Создать src/core/clients/
- [ ] Task 2: Обновить telegram_clients
- [ ] Task 3: Обновить notifications
- [ ] Task 4: Обновить документацию
- [ ] Task 5: Финальная проверка (тесты, linter, коммит)

---

**Plan complete. Two execution options:**

**1. Subagent-Driven (recommended)** — Dispatch fresh subagent per task, review between tasks

**2. Inline Execution** — Execute tasks in this session using executing-plans

**Which approach?**
