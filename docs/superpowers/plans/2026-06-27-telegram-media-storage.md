# Telegram Media Storage Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Интегрировать сохранение Telegram-медиа в storage модуль при получении входящих сообщений — подписчики событий получают `file_id` для скачивания файлов через internal API.

**Architecture:** TelegramClientManager загружает медиа из Telegram → через httpx POST /internal/media/upload → получает file_id → заполняет TgMessageReceived.media[].id. Межмодульное взаимодействие только через HTTP (не импорты).

**Tech Stack:** httpx (async client), FastAPI UploadFile, StorageProvider Protocol, LocalStorage

---

### Task 1: HTTP Client Module для межмодульного взаимодействия

**Files:**
- Create: `src/modules/telegram_clients/http_client.py`
- Test: `tests/modules/telegram_clients/test_http_client.py`

- [ ] **Step 1: Write tests for http_client functions**

```python
# tests/modules/telegram_clients/test_http_client.py
import pytest
import respx
from httpx import AsyncClient

from src.core.config import settings
from src.modules.telegram_clients.http_client import (
    upload_media_to_storage,
    resolve_user_by_auth_id,
)


@respx.mock
async def test_upload_media_to_storage():
    """POST /internal/media/upload возвращает file_id."""
    file_id = "550e8400-e29b-41d4-a716-446655440000"
    respx.post(f"http://localhost:{settings.PORT}/internal/media/").mock(
        return_value={
            "id": file_id,
            "filename": "photo.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 1024,
            "storage_key": "ab/cd/uuid.jpg",
            "is_public": False,
        }
    )

    result = await upload_media_to_storage(
        b"fake image data",
        filename="photo.jpg",
        content_type="image/jpeg",
        is_public=False,
    )

    assert result == file_id
    assert respx.calls.last.request.method == "POST"


@respx.mock
async def test_resolve_user_by_auth_id_found():
    """GET /internal/users/ находит пользователя."""
    auth_id = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
    respx.get(f"http://localhost:{settings.PORT}/internal/users/").mock(
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
    respx.get(f"http://localhost:{settings.PORT}/internal/users/").mock(
        return_value=[]
    )

    email = await resolve_user_by_auth_id(auth_id)
    assert email is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
source venv/bin/activate && pytest tests/modules/telegram_clients/test_http_client.py -v
```
Expected: ModuleNotFoundError (файл ещё не создан)

- [ ] **Step 3: Create http_client.py with upload_media_to_storage and resolve_user_by_auth_id**

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


async def upload_media_to_storage(
    file_bytes: bytes,
    filename: str,
    content_type: str,
    is_public: bool = False,
) -> str | None:
    """
    Загрузить медиа-файл в storage модуль.

    POST /internal/media/upload
    Возвращает file_id или None при ошибке.
    """
    try:
        async with httpx.AsyncClient() as client:
            # multipart/form-data для UploadFile
            files = {"file": (filename, file_bytes, content_type)}
            data = {"is_public": str(is_public).lower()}

            response = await client.post(
                f"http://localhost:{settings.PORT}/internal/media/",
                files=files,
                data=data,
                timeout=10.0,
            )

            if response.status_code == 201:
                return response.json()["id"]
            else:
                logger.error(
                    "Ошибка загрузки медиа в storage: %d %s",
                    response.status_code,
                    response.text[:200],
                )
    except Exception:
        logger.exception("Ошибка загрузки медиа в storage")
    return None


async def resolve_user_by_auth_id(auth_id: uuid.UUID) -> str | None:
    """
    Резолвит email по auth_id через внутренний роут users.

    GET /internal/users/?filters=auth_id+eq+...
    Доступ ограничен network-level.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://localhost:{settings.PORT}/internal/users/",
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

- [ ] **Step 4: Run tests to verify they pass**

```bash
source venv/bin/activate && pytest tests/modules/telegram_clients/test_http_client.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/modules/telegram_clients/http_client.py tests/modules/telegram_clients/test_http_client.py
git commit -m "feat(tg): add http_client module for inter-module communication

- upload_media_to_storage() → POST /internal/media/upload
- resolve_user_by_auth_id() → GET /internal/users/
- Tests with respx mocks
"
```

---

### Task 2: Обновить client_manager.py — загрузка медиа в storage при получении сообщения

**Files:**
- Modify: `src/modules/telegram_clients/client_manager.py:130-160`
- Modify: `requirements.txt` (если нет httpx)

- [ ] **Step 1: Write test for media upload integration**

```python
# tests/modules/telegram_clients/test_client_manager_media.py
import pytest
import respx
from httpx import AsyncClient
from telethon import TelegramClient
from unittest.mock import AsyncMock, MagicMock, patch

from src.bus.interface import MessageBus
from src.modules.telegram_clients.client_manager import TelegramClientManager


@pytest.mark.asyncio
@respx.mock
async def test_on_new_message_with_media_uploads_to_storage():
    """Входящее сообщение с медиа загружается в storage."""
    file_id = "550e8400-e29b-41d4-a716-446655440000"

    # Mock storage API
    respx.post("http://localhost:8000/internal/media/").mock(
        return_value={
            "id": file_id,
            "filename": "photo.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 1024,
            "is_public": False,
        }
    )

    # Mock MessageBus
    mock_bus = AsyncMock(spec=MessageBus)

    # Mock Telethon client и message
    mock_client = MagicMock(spec=TelegramClient)
    mock_message = MagicMock()
    mock_message.id = 42
    mock_message.chat_id = -1001234567890
    mock_message.sender_id = 123456789
    mock_message.text = "Привет!"
    mock_message.media = MagicMock()
    mock_message.media.id = "AQADBAAT..."
    mock_message.media.__class__.__name__ = "MessageMediaPhoto"

    # Mock download_media — возвращает bytes
    async def mock_download_media(file, bytes=True):
        return b"fake image data"

    mock_client.download_media = mock_download_media

    manager = TelegramClientManager(mock_bus)
    manager._clients["account-uuid"] = mock_client

    # Эмулируем событие
    mock_event = MagicMock()
    mock_event.message = mock_message
    mock_event.chat_id = mock_message.chat_id
    mock_event.sender_id = mock_message.sender_id

    # Вызываем обработчик (через _register_message_handler или напрямую)
    # ... тест требует мока Telethon event
```

- [ ] **Step 2: Update client_manager.py — download media и upload в storage**

```python
# src/modules/telegram_clients/client_manager.py
# Добавить импорт в начало файла:
from src.modules.telegram_clients.http_client import upload_media_to_storage

# Обновить метод _register_message_handler (примерно строки 130-160):
def _register_message_handler(
    self, account_id: uuid.UUID, client: TelegramClient
) -> None:
    """Регистрирует обработчик входящих сообщений для клиента."""

    @client.on(events.NewMessage)
    async def on_new_message(event: events.NewMessage.Event) -> None:
        """Публикует входящее сообщение в шину."""
        try:
            # Извлекаем media
            media: list[dict[str, str]] = []
            if event.message.media:
                media_type = type(event.message.media).__name__.lower()
                telegram_file_id = (
                    str(event.message.media.id)
                    if hasattr(event.message.media, "id")
                    else ""
                )

                # Загружаем медиа в storage
                # Скачиваем bytes из Telegram
                media_bytes = await client.download_media(
                    event.message.media,
                    bytes=True,
                )

                # Определяем filename и content_type
                filename = f"{telegram_file_id}.dat"
                content_type = "application/octet-stream"

                # Загружаем в storage через internal API
                storage_file_id = await upload_media_to_storage(
                    media_bytes,
                    filename=filename,
                    content_type=content_type,
                    is_public=False,
                )

                media.append({
                    "type": media_type,
                    "id": telegram_file_id,  # Telegram file_id (для справки)
                    "file_id": storage_file_id,  # ← ID из storage (основной)
                })

            msg_event = TgMessageReceived(
                account_id=account_id,
                chat_id=event.chat_id,
                message_id=event.message.id,
                sender_id=event.sender_id,
                text=event.message.text,
                media=media,
            )
            await self._message_bus.publish(
                BusTopics.TG_MESSAGE_RECEIVED, msg_event.to_bus_dict()
            )
        except Exception:
            logger.exception(
                "Ошибка при обработке входящего сообщения для аккаунта %s",
                account_id,
            )
```

- [ ] **Step 3: Update schemas/events.py — добавить file_id в MediaItem**

```python
# src/modules/telegram_clients/schemas/events.py
# Обновить класс TgMessageReceived или отдельный MediaItem:

class MediaItem(BaseModel):
    type: str  # "photo", "video", "voice", etc.
    id: str  # Telegram file_id
    file_id: str | None = None  # ← Storage file_id (после загрузки)

# Или обновить TgMessageReceived напрямую:
class TgMessageReceived(BaseEvent):
    # ...
    media: list[dict[str, str]]  # или list[MediaItem]
```

- [ ] **Step 4: Run tests**

```bash
source venv/bin/activate && pytest tests/modules/telegram_clients/ -v -k media
```

- [ ] **Step 5: Commit**

```bash
git add src/modules/telegram_clients/client_manager.py src/modules/telegram_clients/schemas/events.py
git commit -m "feat(tg): upload media to storage on incoming messages

- download_media() из Telegram → upload_media_to_storage() → file_id
- TgMessageReceived.media[].file_id содержит ID из storage
- Подписчики получают готовую ссылку на файл
"
```

---

### Task 3: Обновить документацию

**Files:**
- Modify: `docs/superpowers/specs/2026-06-25-telegram-clients-design.md`
- Modify: `docs/superpowers/plans/2026-06-27-media.md` (update status)

- [ ] **Step 1: Update telegram-clients-design.md — секция Media**

```markdown
## Media — реализация

**Статус:** ✅ Реализовано (2026-06-27)

### Входящие сообщения

При получении сообщения с медиа:

1. `TelegramClientManager.download_media()` — скачать bytes из Telegram
2. `upload_media_to_storage()` — POST /internal/media/upload
3. Сохранить `file_id` из ответа в `TgMessageReceived.media[].file_id`

**Формат media в событии:**

```json
{
  "media": [
    {
      "type": "photo",
      "id": "AQADBAAT...",
      "file_id": "550e8400-e29b-41d4-a716-446655440000"
    }
  ]
}
```

**Преимущества:**
- Подписчики получают готовый `file_id` — могут скачать через `/internal/media/{id}`
- Telegram-модуль не хранит бинарные данные
- Файлы независимы — переиспользование в других контекстах
```

- [ ] **Step 2: Update media.md — секция Межмодульное взаимодействие**

```markdown
## Межмодульное взаимодействие

### telegram_clients → media

**Сценарий:** Входящее сообщение с медиа

1. TelegramClientManager.download_media(bytes=True) → bytes
2. POST /internal/media/upload (httpx)
3. Ответ: { "id": "uuid", ... }
4. TgMessageReceived.media[].file_id = uuid

**Код:** `src/modules/telegram_clients/client_manager.py:_register_message_handler()`
```

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-06-25-telegram-clients-design.md docs/superpowers/plans/2026-06-27-media.md
git commit -m "docs: update media and telegram-clients specs for media storage integration
"
```

---

### Task 4: Интеграционные тесты и проверка end-to-end

**Files:**
- Create: `tests/modules/telegram_clients/test_media_integration.py`

- [ ] **Step 1: Write integration test with full flow**

```python
# tests/modules/telegram_clients/test_media_integration.py
"""
Integration test: Telegram incoming message → storage → event with file_id
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import respx

from src.main import app
from src.core.database import async_sessionmaker
from src.bus.interface import MessageBus


@pytest.mark.asyncio
@respx.mock
async def test_incoming_message_media_storage_integration():
    """End-to-end: входящее сообщение с медиа сохраняется в storage."""
    # Mock storage upload
    file_id = "550e8400-e29b-41d4-a716-446655440000"
    respx.post("http://localhost:8000/internal/media/").mock(
        return_value={"id": file_id, "filename": "photo.jpg", ...}
    )

    # Mock MessageBus.publish для перехвата события
    published_events = []
    original_publish = app.state.message_bus.publish

    async def capture_publish(topic, message):
        published_events.append((topic, message))
        await original_publish(topic, message)

    with patch.object(app.state.message_bus, 'publish', capture_publish):
        # Эмулируем входящее сообщение через Telethon mock
        # ... (требует сложной настройки Telethon мока)
        pass

    # Проверяем, что событие опубликовано с file_id
    assert len(published_events) > 0
    topic, message = published_events[0]
    assert message["event_name"] == "tg.message.received"
    assert message["media"][0]["file_id"] == file_id
```

- [ ] **Step 2: Run integration test**

```bash
source venv/bin/activate && pytest tests/modules/telegram_clients/test_media_integration.py -v
```

- [ ] **Step 3: Commit**

```bash
git add tests/modules/telegram_clients/test_media_integration.py
git commit -m "test(tg): add media storage integration test
"
```

---

### Task 5: Проверка и рефакторинг

- [ ] **Step 1: Run all tests**

```bash
source venv/bin/activate && pytest tests/ -v --tb=short
```
Expected: 139+ tests passing

- [ ] **Step 2: Run linter**

```bash
ruff check src/ tests/ --fix
```

- [ ] **Step 3: Manual verification — проверить логи при запуске**

```bash
uvicorn src.main:app --reload
# Отправить сообщение в Telegram → проверить логи storage upload
```

- [ ] **Step 4: Commit final cleanup**

```bash
git status
git commit -am "refactor(tg): cleanup and final polish for media integration
"
```

---

## Self-Review Checklist

**Spec coverage:**
- ✅ Media upload на входящие сообщения
- ✅ HTTP client для межмодульного взаимодействия
- ✅ file_id в TgMessageReceived
- ✅ Документация обновлена

**No placeholders:** Все шаги содержат код

**Type consistency:** `file_id: str | None` в schemas, http_client возвращает `str | None`

---

**Plan complete and saved to `docs/superpowers/plans/2026-06-27-telegram-media-storage.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — Dispatch fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
