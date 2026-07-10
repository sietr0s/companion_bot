# Media Module Design Spec

**Дата:** 2026-06-27
**Статус:** Approved
**Модуль:** `src/modules/media/`

---

## Цель

Универсальное файловое хранилище для модульного монолита. MVP — файлы на диске (папка), в будущем — бесшовный переход на S3. Файлы — независимые сущности без привязки к владельцам, доступ контролируется через `is_public` флаг и внутренний API.

---

## Требования

1. **Универсальность** — любой модуль может сохранить файл (TG медиа, аватарки, вложения)
2. **Изоляция** — модули не вызывают MediaService напрямую, только через internal API (httpx) или шину событий
3. **Готовность к микросервисам** — при выносе меняется только base URL httpx-клиента
4. **Гибридный доступ** — публичные файлы по прямой ссылке, приватные — только через internal API
5. **S3-ready** — StorageProvider Protocol с двумя реализациями: LocalStorage (MVP), S3Storage (future)
6. **Лимит** — до 50 МБ на файл

---

## Модель данных

### StoredFile

Модуль: `src/modules/media/models.py`

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| id | UUID | PK, default=uuid4 | Идентификатор файла |
| filename | VARCHAR(500) | NOT NULL | Оригинальное имя файла |
| content_type | VARCHAR(100) | NOT NULL | MIME-тип (image/jpeg, video/mp4, ...) |
| size_bytes | BigInteger | NOT NULL | Размер в байтах |
| storage_key | VARCHAR(500) | NOT NULL, UNIQUE | Путь/ключ в хранилище |
| is_public | Boolean | DEFAULT FALSE | Публичный доступ по ссылке |
| created_at | TIMESTAMP | NOT NULL | Дата создания |
| updated_at | TIMESTAMP | NOT NULL | Дата обновления |

Файл — независимая сущность. Никакого `auth_id`, никакого `owner_type`. Модули-потребители хранят `file_id` в своих таблицах.

---

## StorageProvider Protocol

Модуль: `src/modules/media/storage/base.py`

```python
class StorageProvider(Protocol):
    async def put(self, key: str, data: bytes, content_type: str) -> str:
        """Сохранить файл, вернуть key."""

    async def get(self, key: str) -> bytes:
        """Прочитать файл из хранилища."""

    async def delete(self, key: str) -> None:
        """Удалить файл."""

    async def generate_url(self, key: str, expires: int = 3600) -> str:
        """Сгенерировать URL для скачивания."""
```

### LocalStorage

Модуль: `src/modules/media/storage/local.py`

- Сохраняет в папку `MEDIA_STORAGE_PATH` (из конфига, default `uploads/`)
- Ключ = `{shard_2}/{shard_2}/{uuid4}.{ext}` — 2-level sharding для FS-производительности
  - Пример: `uploads/ab/cd/abcd1234-5678-...jpg`
- `generate_url` возвращает `/media/{id}/download` (внутренний роут)
- При старте создаёт папку `MEDIA_STORAGE_PATH` если не существует

### S3Storage (future)

Модуль: `src/modules/media/storage/s3.py` (не реализуется в MVP)

- aiobotocore
- Ключ = `media/{uuid4}.{ext}`
- `generate_url` возвращает presigned URL с TTL
- Конфиг: `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`

---

## Конфигурация

Добавляется в `src/core/config.py`:

```python
# Media
MEDIA_STORAGE_PROVIDER: str = "local"    # "local" | "s3"
MEDIA_STORAGE_PATH: str = "uploads"      # для LocalStorage
MEDIA_MAX_SIZE_MB: int = 50              # лимит загрузки

# S3 (на будущее)
# S3_ENDPOINT_URL: str = ""
# S3_BUCKET: str = ""
# S3_ACCESS_KEY: str = ""
# S3_SECRET_KEY: str = ""
```

---

## API

### Публичные роуты

Файл: `src/modules/media/routers/public.py`
Префикс: `/media`

| Метод | Путь | Auth | Описание |
|-------|------|------|----------|
| POST | `/media/upload` | JWT | Загрузить файл (multipart/form-data) |
| GET | `/media/{id}` | нет* | Метаданные файла (JSON) |
| GET | `/media/{id}/download` | нет* | Скачать файл (бинарный ответ) |
| DELETE | `/media/{id}` | JWT | Удалить файл |

*Для GET: если `is_public=True` — доступ свободно, если `is_public=False` — 404.

**Upload-запрос:**
```
POST /media/upload
Content-Type: multipart/form-data
Authorization: Bearer <token>

file: <binary>
is_public: false (опционально, default false)
```

**Upload-ответ (201):**
```json
{
  "id": "uuid",
  "filename": "photo.jpg",
  "content_type": "image/jpeg",
  "size_bytes": 123456,
  "storage_key": "ab/cd/abcd1234.jpg",
  "is_public": false,
  "created_at": "...",
  "updated_at": "..."
}
```

**Ошибки:**

| Статус | Описание |
|--------|----------|
| 404 | Файл не найден / файл приватный (для публичного роута) |
| 413 | Файл превышает MEDIA_MAX_SIZE_MB |
| 415 | Неподдерживаемый content_type (опционально) |

### Internal-роуты

Файл: `src/modules/media/routers/internal.py`
Префикс: `/internal/media`

Без JWT, доступ network-level (Docker network, k8s NetworkPolicy).

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/internal/media/upload` | Загрузить файл (multipart) |
| GET | `/internal/media/{id}` | Метаданные (любой файл, включая приватные) |
| GET | `/internal/media/{id}/download` | Скачать (любой файл) |
| DELETE | `/internal/media/{id}` | Удалить файл |

Internal-роуты не проверяют `is_public` — отдают любой файл по ID.

---

## Межмодульное взаимодействие

Модули работают с media **только** через internal API (httpx) или шину событий. Прямой вызов MediaService из других модулей запрещён.

### Через httpx (request-response)

```python
# Пример: telegram_clients сохраняет медиа
async with httpx.AsyncClient() as client:
    resp = await client.post(
        "http://localhost:8000/internal/media/upload",
        files={"file": (filename, media_bytes, content_type)},
        data={"is_public": "false"},
    )
file_id = resp.json()["id"]
```

```python
# Пример: получение приватного файла
async with httpx.AsyncClient() as client:
    resp = await client.get(
        f"http://localhost:8000/internal/media/{file_id}/download"
    )
file_bytes = resp.content
```

При выносе media в микросервис — меняется только base URL в конфиге.

### Через шину событий (fire-and-forget)

Топики в `BusTopics`:

```python
MEDIA_UPLOADED: str = "media.uploaded"
MEDIA_DELETED: str = "media.deleted"
```

События:

**MediaUploaded:**

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"media.uploaded"` |
| file_id | UUID | ID загруженного файла |
| filename | str | Имя файла |
| content_type | str | MIME-тип |
| size_bytes | int | Размер |
| is_public | bool | Публичный ли |

**MediaDeleted:**

| Поле | Тип | Описание |
|------|-----|----------|
| event_name | str | `"media.deleted"` |
| file_id | UUID | ID удалённого файла |

---

## Структура модуля

```
src/modules/media/
├── __init__.py
├── models.py                # StoredFile
├── schemas/
│   ├── __init__.py
│   ├── api.py               # FileRead, FileUploadResponse
│   └── events.py            # MediaUploaded, MediaDeleted
├── repository.py            # StoredFileRepository
├── storage/
│   ├── __init__.py
│   ├── base.py              # StorageProvider (Protocol)
│   └── local.py             # LocalStorage
├── service.py               # MediaService
├── handlers.py              # Подписка на шину (future side-effects)
└── routers/
    ├── __init__.py           # from .public import public_router
    │                         # from .internal import internal_router
    ├── public.py             # /media/ — upload, get, download, delete
    └── internal.py           # /internal/media/ — upload, get, download, delete
```

---

## Регистрация в main.py

```python
from src.modules.media.routers import public_router, internal_router

app.include_router(public_router, prefix="/media", tags=["Media"])
app.include_router(internal_router, prefix="/internal/media", tags=["Internal"])
```

---

## MediaService

Модуль: `src/modules/media/service.py`

```python
class MediaService:
    def __init__(self, repository, storage_provider, message_bus): ...

    async def upload(self, session, filename, data, content_type, is_public=False) -> StoredFile
    async def get(self, session, file_id) -> StoredFile
    async def download(self, session, file_id) -> bytes
    async def delete(self, session, file_id) -> None
```

- `upload` — генерирует storage_key (2-level shard + UUID + ext), сохраняет через StorageProvider, создаёт запись в БД, публикует `MEDIA_UPLOADED`
- `download` — читает через StorageProvider
- `delete` — удаляет из хранилища и БД, публикует `MEDIA_DELETED`

---

## Зависимости

Новые зависимости в `requirements.txt`:
- `python-multipart>=0.0.6` — для FastAPI UploadFile (multipart/form-data)

---

## Тестирование

- Unit-тесты: StorageProvider Protocol, LocalStorage, MediaService
- Интеграционные: публичные роуты (upload, get, download, delete), internal-роуты
- Проверка: is_public=False → публичный роут возвращает 404, internal — 200
- Проверка: лимит размера файла (413)
- Фикстуры: тестовые файлы в `tests/fixtures/`
