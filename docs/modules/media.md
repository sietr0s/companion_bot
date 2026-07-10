# Модуль MEDIA

**Расположение**: `src/modules/media/`

## Назначение

Управление файлами: загрузка, хранение, скачивание, удаление. Поддерживает абстракцию `StorageProvider` для замены хранилища (LocalStorage, S3).

## Бизнес-логика

### Основные возможности

- Загрузка файлов (images, documents, audio, video)
- Хранение метаданных файлов в БД
- Скачивание файлов (полное и потоковое)
- Удаление файлов
- Управление доступом (public/private)
- 2-level sharding для хранения файлов
- Поддержка различных провайдеров (Local, S3)

## Модели данных

### StoredFile

```python
class StoredFile(BaseModel):
    """Хранимый файл"""
    
    id: UUID                      # Уникальный ID файла
    filename: str                 # Оригинальное имя файла
    content_type: str             # MIME-тип (image/png, application/pdf)
    size_bytes: int               # Размер в байтах
    storage_key: str              # Уникальный ключ в хранилище
    is_public: bool = False       # Публичный доступ
    created_at: datetime          # Дата загрузки
    uploaded_by: UUID | None      # Кто загрузил (auth_id)
```

**Индексы:**
- `ix_stored_file_storage_key` — уникальный индекс на storage_key
- `ix_stored_file_is_public` — для фильтрации публичных файлов
- `ix_stored_file_uploaded_by` — для поиска по загрузившему пользователю

## Репозиторий

### StoredFileRepository

**Расположение**: `src/modules/media/repository.py`

```python
class StoredFileRepository(BaseRepository[StoredFile]):
    """Репозиторий для работы с файлами"""
    
    # Методы без дополнительной логики, только CRUD
```

**Методы:**
- Стандартные CRUD методы от `BaseRepository`: `get`, `get_all`, `create`, `update`, `delete`

## Сервис

### MediaService

**Расположение**: `src/modules/media/service.py`

```python
class MediaService(BaseService[StoredFileRepository]):
    """Бизнес-логика управления файлами"""
```

### Методы

#### upload
```python
async def upload(
    self,
    session: AsyncSession,
    filename: str,
    data: bytes,
    content_type: str,
    is_public: bool = False,
) -> StoredFile:
    """
    Загрузка файла
    
    - Генерирует storage_key (sharding)
    - Сохраняет файл в хранилище
    - Создаёт запись в БД
    - Публикует событие MEDIA_UPLOADED
    
    Returns:
        StoredFile: Метаданные файла
    """
```

#### get
```python
async def get(
    self, session: AsyncSession, file_id: UUID
) -> StoredFile:
    """
    Получение метаданных файла
    
    Raises:
        NotFoundError: Если файл не найден
    """
```

#### download
```python
async def download(
    self, session: AsyncSession, file_id: UUID
) -> tuple[StoredFile, bytes]:
    """
    Скачивание файла
    
    - Получает метаданные из БД
    - Загружает файл из хранилища
    - Возвращает метаданные + содержимое
    
    Raises:
        NotFoundError: Если файл не найден
        ForbiddenError: Если файл private и нет доступа
    """
```

#### download_stream
```python
async def download_stream(
    self, session: AsyncSession, file_id: UUID
) -> tuple[StoredFile, AsyncGenerator[bytes, None]]:
    """
    Потоковое скачивание файла
    
    - Получает метаданные из БД
    - Возвращает поток для чтения файла по чанкам
    
    Raises:
        NotFoundError: Если файл не найден
    """
```

#### delete
```python
async def delete(
    self, session: AsyncSession, file_id: UUID
) -> None:
    """
    Удаление файла
    
    - Удаляет файл из хранилища
    - Удаляет запись из БД
    - Публикует событие MEDIA_DELETED
    
    Raises:
        NotFoundError: Если файл не найден
    """
```

#### get_user_files
```python
async def get_user_files(
    self,
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    filters: MediaFilters | None = None,
) -> list[StoredFile]:
    """
    Получение списка файлов пользователя с пагинацией
    
    Фильтры:
    - is_public: фильтр по публичности
    - content_type: фильтр по MIME-типу
    - created_from: дата создания
    - created_to: дата создания
    """
```

#### update_file
```python
async def update_file(
    self,
    session: AsyncSession,
    file_id: UUID,
    is_public: bool | None = None,
    filename: str | None = None,
) -> StoredFile:
    """
    Обновление метаданных файла
    
    - Обновляет is_public и/или filename
    - Возвращает обновлённый файл
    
    Raises:
        NotFoundError: Если файл не найден
    """
```

## Хранилища

### StorageProvider (Protocol)

**Расположение**: `src/modules/media/storage/base.py`

```python
class StorageProvider(Protocol):
    """
    Protocol для провайдера хранилища
    
    Определяет интерфейс для всех реализаций хранилищ
    """
    
    async def put(
        self, key: str, data: bytes, content_type: str
    ) -> str:
        """
        Сохранение файла
        
        Returns:
            str: URL или ключ для доступа к файлу
        """
    
    async def get(self, key: str) -> bytes:
        """Получение файла"""
    
    async def get_stream(
        self, key: str
    ) -> AsyncGenerator[bytes, None]:
        """Потоковое чтение файла"""
    
    async def delete(self, key: str) -> None:
        """Удаление файла"""
    
    async def generate_url(
        self, key: str, expires: int | None = None
    ) -> str:
        """
        Генерация URL для доступа к файлу
        
        Параметры:
        - expires: время жизни URL в секундах (для signed URL)
        """
```

### LocalStorage

**Расположение**: `src/modules/media/storage/local.py`

```python
class LocalStorage(StorageProvider):
    """
    Локальное файловое хранилище
    
    Использует 2-level sharding для равномерного распределения файлов
    """
    
    CHUNK_SIZE = 64 * 1024  # 64KB для потокового чтения
```

#### Методы

```python
def _get_sharded_path(self, filename: str) -> Path:
    """
    Генерация пути с 2-level sharding
    
    Пример:
    - filename: "550e8400-e29b-41d4-a716-446655440000.png"
    - путь: "files/55/0e/550e8400-e29b-41d4-a716-446655440000.png"
    
    Sharding обеспечивает:
    - Равномерное распределение по директориям
    - Избегание проблем с большим количеством файлов в одной папке
    """
```

## HTTP API

### Публичные роуты

**Расположение**: `src/modules/media/routers/public.py`

| Метод | Путь | Описание | Auth |
|-------|------|----------|------|
| `POST` | `/public/media/upload` | Загрузка файла | ✅ JWT |
| `GET` | `/public/media/{file_id}` | Метаданные (только public) | ❌ |
| `GET` | `/public/media/{file_id}/download` | Скачивание (только public) | ❌ |
| `DELETE` | `/public/media/{file_id}` | Удаление файла | ✅ JWT |

#### Примеры запросов

**Загрузка файла:**
```bash
POST /public/media/upload
Content-Type: multipart/form-data
Authorization: Bearer <token>

file: <binary>
is_public: false
```

**Ответ:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "document.pdf",
  "content_type": "application/pdf",
  "size_bytes": 1024000,
  "storage_key": "files/d0/cu/d0cuf834-...",
  "is_public": false,
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Скачивание публичного файла:**
```bash
GET /public/media/{file_id}/download
```

**Ответ:**
- Content-Type: из метаданных файла
- Content-Disposition: attachment; filename="..."
- Body: бинарные данные файла

### Внутренние роуты

**Расположение**: `src/modules/media/routers/internal.py`

| Метод | Путь | Описание | Auth |
|-------|------|----------|------|
| `GET` | `/internal/media/` | Список всех файлов | ❌ |
| `POST` | `/internal/media/upload` | Загрузка файла (без JWT) | ❌ |
| `GET` | `/internal/media/{file_id}` | Метаданные любого файла | ❌ |
| `GET` | `/internal/media/{file_id}/download` | Скачивание любого файла | ❌ |
| `DELETE` | `/internal/media/{file_id}` | Удаление (без JWT) | ❌ |

## События шины

### Публикации (исходящие)

#### MediaUploaded
```python
class MediaUploaded(BaseEvent):
    """Файл загружен"""
    
    file_id: UUID
    filename: str
    content_type: str
    size_bytes: int
    uploaded_by: UUID | None
```

**Топик**: `media.uploaded`

**Когда публикуется:**
- После успешной загрузки файла через `upload()`

**Подписчики:**
- Нет (событие для будущего расширения)

#### MediaDeleted
```python
class MediaDeleted(BaseEvent):
    """Файл удалён"""
    
    file_id: UUID
    storage_key: str
```

**Топик**: `media.deleted`

**Когда публикуется:**
- После удаления файла через `delete()`

**Подписчики:**
- Нет (событие для будущего расширения)

## Обработчики шины

**Расположение**: `src/modules/media/handlers.py`

```python
# Пока пусто — модуль только публикует события
# Обработчики могут быть добавлены для:
# - Аудита загрузки файлов
# - Генерации превью для изображений
# - Вирусканнинга загруженных файлов
```

## DI-зависимости

**Расположение**: `src/modules/media/dependencies.py`

```python
def get_stored_file_repository() -> StoredFileRepository:
    """Фабрика репозитория"""
    return StoredFileRepository()


def get_storage_provider() -> StorageProvider:
    """
    Фабрика провайдера хранилища
    
    Возвращает LocalStorage по умолчанию
    Для S3 вернуть S3Storage
    """
    return LocalStorage(root_path=settings.MEDIA_ROOT)


def get_media_service(
    repo: Annotated[StoredFileRepository, Depends(get_stored_file_repository)],
    storage: Annotated[StorageProvider, Depends(get_storage_provider)],
    message_bus: Annotated[MessageBus, Depends(get_message_bus)],
) -> MediaService:
    """Фабрика сервиса"""
    return MediaService(
        repository=repo,
        storage_provider=storage,
        message_bus=message_bus,
    )
```

## Константы

**Расположение**: `src/modules/media/constants.py`

### MediaType

```python
class MediaType(str, Enum):
    IMAGE = "image"           # Изображения (png, jpg, gif, webp)
    VIDEO = "video"           # Видео (mp4, avi, mov)
    AUDIO = "audio"           # Аудио (mp3, wav, ogg)
    DOCUMENT = "document"     # Документы (pdf, docx, xlsx)
    TEXT = "text"             # Текстовые файлы (txt, md)
```

### MEDIA_TYPES

```python
MEDIA_TYPES = {
    # Изображения
    "image/png": MediaType.IMAGE,
    "image/jpeg": MediaType.IMAGE,
    "image/gif": MediaType.IMAGE,
    "image/webp": MediaType.IMAGE,
    
    # Видео
    "video/mp4": MediaType.VIDEO,
    "video/quicktime": MediaType.VIDEO,
    
    # Аудио
    "audio/mpeg": MediaType.AUDIO,
    "audio/wav": MediaType.AUDIO,
    
    # Документы
    "application/pdf": MediaType.DOCUMENT,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": MediaType.DOCUMENT,
    
    # Текст
    "text/plain": MediaType.TEXT,
    "text/markdown": MediaType.TEXT,
}
```

### ERROR_MESSAGES

```python
ERROR_MESSAGES = {
    "file_not_found": "Файл не найден",
    "access_denied": "Доступ запрещён",
    "file_too_large": "Файл слишком большой",
    "invalid_content_type": "Недопустимый тип файла",
    "storage_error": "Ошибка хранилища",
}
```

### Лимиты

```python
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB для изображений
```

## Взаимосвязи с другими модулями

### Зависит от

| Модуль | Тип | Описание |
|--------|-----|----------|
| `bus` | Шина | Публикация событий о загрузке/удалении |

### Используется

| Модуль | Тип | Описание |
|--------|-----|----------|
| `telegram_clients` | MediaClient | Загрузка медиа из сообщений |

## Клиенты (межмодульное взаимодействие)

### MediaClient

**Расположение**: `src/core/clients/media_client.py`

```python
class MediaClient:
    """Клиент для взаимодействия с media модулем"""
    
    async def upload_media(
        self,
        session: AsyncSession,
        filename: str,
        data: bytes,
        content_type: str,
        is_public: bool = False,
    ) -> StoredFile:
        """
        Загрузка медиа
    
        Returns:
            StoredFile: Метаданные файла
        """
    
    async def upload_media_list(
        self,
        session: AsyncSession,
        media_list: list[MediaItem],
    ) -> list[StoredFile]:
        """
        Массовая загрузка медиа
    
        Returns:
            list[StoredFile]: Список загруженных файлов
        """
```

## Примеры использования

### Загрузка файла

```python
async with session.begin():
    file = await service.upload(
        session=session,
        filename="document.pdf",
        data=file_bytes,
        content_type="application/pdf",
        is_public=False,
    )
    # file.id содержит UUID загруженного файла
```

### Скачивание файла

```python
async with session.begin():
    file_meta, file_data = await service.download(
        session=session,
        file_id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
    )
    # file_meta: StoredFile
    # file_data: bytes
```

### Потоковое скачивание

```python
from fastapi.responses import StreamingResponse

async def download_file_endpoint(
    file_id: UUID,
    service: Annotated[MediaService, Depends(get_media_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    file_meta, stream = await service.download_stream(session, file_id)
    
    return StreamingResponse(
        stream,
        media_type=file_meta.content_type,
        headers={
            "Content-Disposition": f"attachment; filename=\"{file_meta.filename}\""
        }
    )
```

### Массовая загрузка медиа

```python
# В telegram_clients/handlers.py
media_list = message.get("media", [])  # Список MediaItem из Telegram

uploaded_files = await media_client.upload_media_list(
    session=session,
    media_list=media_list,
)

# uploaded_files: list[StoredFile]
```

## Тестирование

**Расположение тестов**: `tests/modules/media/`

### Фикстуры

```python
@pytest.fixture
def media_service(repository, storage_provider, message_bus):
    return MediaService(
        repository=repository,
        storage_provider=storage_provider,
        message_bus=message_bus,
    )


@pytest.fixture
def storage_provider(tmp_path):
    return LocalStorage(root_path=tmp_path / "media")


@pytest.fixture
def repository(db_session):
    return StoredFileRepository()
```

### Пример теста

```python
async def test_upload_file(db_session, media_service, tmp_path):
    file_bytes = b"test file content"
    
    file = await media_service.upload(
        session=db_session,
        filename="test.txt",
        data=file_bytes,
        content_type="text/plain",
        is_public=False,
    )
    
    assert file.filename == "test.txt"
    assert file.content_type == "text/plain"
    assert file.size_bytes == len(file_bytes)
    assert file.is_public is False
```

## Миграции Alembic

**Файл миграции**: `alembic/versions/XXXX_create_media_table.py`

```python
def upgrade():
    op.create_table(
        'stored_files',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('content_type', sa.String(), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('storage_key', sa.String(), nullable=False),
        sa.Column('is_public', sa.Boolean(), nullable=False, default=False),
        sa.Column('uploaded_by', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_stored_file_storage_key', 'stored_files', ['storage_key'], unique=True)
    op.create_index('ix_stored_file_is_public', 'stored_files', ['is_public'])
    op.create_index('ix_stored_file_uploaded_by', 'stored_files', ['uploaded_by'])
```

## Конфигурация

### Переменные окружения

```bash
# MEDIA_ROOT=/app/media
MEDIA_ROOT=./media

# MEDIA_MAX_SIZE=52428800  # 50 MB
MEDIA_MAX_SIZE=52428800

# STORAGE_PROVIDER=local  # local или s3
STORAGE_PROVIDER=local

# S3 параметры (если STORAGE_PROVIDER=s3)
S3_BUCKET=
S3_ACCESS_KEY=
S3_SECRET_KEY=
S3_ENDPOINT_URL=
S3_REGION=
```

## Дополнительные материалов

- [telegram_clients.md](telegram_clients.md) — загрузка медиа из Telegram
- [STYLEGUIDE.md](../../STYLEGUIDE.md) — стиль кода
