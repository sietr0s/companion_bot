# Модуль USERS

**Расположение**: `src/modules/users/`

## Назначение

Управление профилями пользователей: создание, чтение, обновление, удаление. Также управление связанными Telegram-профилями. Модуль изолирован от auth — `auth_id` приходит из JWT и используется как внешний идентификатор.

## Бизнес-логика

### Основные возможности

- Создание профиля пользователя после регистрации
- Чтение и обновление профиля
- Удаление профиля
- Привязка Telegram-аккаунта к профилю
- Получение списка пользователей с фильтрацией
- Резолвинг email по auth_id (для других модулей)

## Модели данных

### User

```python
class User(BaseModel):
    """Профиль пользователя"""
    
    id: UUID                      # Уникальный ID профиля
    auth_id: UUID                 # Внешний ID из auth модуля (уникальный, без FK)
    first_name: str | None        # Имя
    last_name: str | None         # Фамилия
    avatar_url: str | None        # URL аватара
    bio: str | None               # О себе
    telegram_id: UUID | None      # Связь с Telegram (FK внутри модуля)
```

**Индексы:**
- `ix_users_auth_id` — уникальный индекс для быстрого поиска по auth_id

### Telegram

```python
class Telegram(BaseModel):
    """Telegram-аккаунт пользователя"""
    
    id: UUID                      # Уникальный ID записи
    telegram_id: int              # ID в Telegram
    telegram_username: str | None # Username в Telegram
    telegram_first_name: str | None  # Имя в Telegram
    telegram_last_name: str | None   # Фамилия в Telegram
```

**Связи:**
- `user` (one-to-one) — связь с профилем пользователя через `telegram_id`

## Репозитории

### UserRepository

**Расположение**: `src/modules/users/repository.py`

```python
class UserRepository(BaseRepository[User]):
    """Репозиторий для работы с профилями пользователей"""
    
    async def get_by_auth_id(
        self, session: AsyncSession, auth_id: UUID
    ) -> User | None:
        """Поиск профиля по auth_id"""
```

**Методы:**
- `get_by_auth_id(session, auth_id)` — поиск профиля по auth_id
- Стандартные CRUD методы от `BaseRepository`

### TelegramRepository

```python
class TelegramRepository(BaseRepository[Telegram]):
    """Репозиторий для работы с Telegram-профилями"""
    
    async def get_by_telegram_id(
        self, session: AsyncSession, telegram_id: int
    ) -> Telegram | None:
        """Поиск Telegram-профиля по telegram_id"""
    
    async def get_by_auth_id(
        self, session: AsyncSession, auth_id: UUID
    ) -> Telegram | None:
        """Поиск Telegram-профиля через User по auth_id"""
    
    async def get_list_with_profiles(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Telegram]:
        """Список Telegram-профилей с данными пользователей"""
```

**Методы:**
- `get_by_telegram_id(session, telegram_id)` — поиск по telegram_id
- `get_by_auth_id(session, auth_id)` — поиск через связь с User
- `get_list_with_profiles(session, skip, limit)` — список с пагинацией
- Стандартные CRUD методы

## Сервис

### UserService

**Расположение**: `src/modules/users/service.py`

```python
class UserService(BaseService[UserRepository, User]):
    """Бизнес-логика управления профилями"""
```

### Публичные методы

#### create_user_profile
```python
async def create_user_profile(
    self, session: AsyncSession, auth_id: UUID, data: UserCreate
) -> User:
    """
    Создание профиля пользователя
    
    - Проверяет что профиль ещё не создан
    - Создаёт новый профиль
    - Публикует событие PROFILE_CREATED
    
    Raises:
        ConflictError: Если профиль уже существует
    """
```

#### get_profile
```python
async def get_profile(
    self, session: AsyncSession, auth_id: UUID
) -> User:
    """
    Получение профиля пользователя
    
    Raises:
        NotFoundError: Если профиль не найден
    """
```

#### update_profile
```python
async def update_profile(
    self,
    session: AsyncSession,
    auth_id: UUID,
    data: UserUpdate,
) -> User:
    """
    Обновление профиля
    
    - Обновляет поля профиля
    - Публикует событие PROFILE_UPDATED
    
    Raises:
        NotFoundError: Если профиль не найден
    """
```

#### delete_profile
```python
async def delete_profile(
    self, session: AsyncSession, auth_id: UUID
) -> None:
    """
    Удаление профиля
    
    - Удаляет профиль из БД
    - Публикует событие PROFILE_DELETED
    
    Raises:
        NotFoundError: Если профиль не найден
    """
```

#### get_users
```python
async def get_users(
    self,
    session: AsyncSession,
    filters: UserFilters,
    skip: int = 0,
    limit: int = 100,
) -> list[User]:
    """
    Получение списка пользователей с фильтрацией
    
    Фильтры:
    - search: поиск по имени/фамилии/email
    - created_from: дата создания
    - created_to: дата создания
    """
```

#### create_telegram_profile
```python
async def create_telegram_profile(
    self,
    session: AsyncSession,
    profile_id: UUID,
    data: TelegramCreate,
) -> Telegram:
    """
    Создание Telegram-профиля
    
    - Привязывает Telegram к пользователю
    - Создаёт запись в БД
    
    Raises:
        ConflictError: Если Telegram уже привязан
    """
```

#### get_profile_with_telegram
```python
async def get_profile_with_telegram(
    self, session: AsyncSession, auth_id: UUID
) -> tuple[User, Telegram | None]:
    """
    Получение профиля с Telegram-данными
    
    Returns:
        tuple[User, Telegram | None]: Профиль и Telegram (если есть)
    """
```

#### get_telegram_by_auth_id
```python
async def get_telegram_by_auth_id(
    self, session: AsyncSession, auth_id: UUID
) -> Telegram | None:
    """
    Получение Telegram-профиля по auth_id
    
    Returns:
        Telegram | None: Telegram-профиль или None
    """
```

## HTTP API

### Публичные роуты

**Расположение**: `src/modules/users/routers/public.py`

| Метод | Путь | Описание | Auth |
|-------|------|----------|------|
| `POST` | `/public/users/` | Создание профиля | ✅ JWT |
| `GET` | `/public/users/me` | Мой профиль | ✅ JWT |
| `PATCH` | `/public/users/me` | Обновление профиля | ✅ JWT |
| `DELETE` | `/public/users/me` | Удаление профиля | ✅ JWT |
| `GET` | `/public/users/me/telegram` | Мой Telegram | ✅ JWT |

#### Примеры запросов

**Создание профиля:**
```bash
POST /public/users/
Content-Type: application/json
Authorization: Bearer <token>

{
  "first_name": "Иван",
  "last_name": "Иванов",
  "bio": "Разработчик"
}
```

**Ответ:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "auth_id": "550e8400-e29b-41d4-a716-446655440001",
  "first_name": "Иван",
  "last_name": "Иванов",
  "avatar_url": null,
  "bio": "Разработчик",
  "telegram_id": null
}
```

**Получение профиля:**
```bash
GET /public/users/me
Authorization: Bearer <token>
```

**Обновление профиля:**
```bash
PATCH /public/users/me
Content-Type: application/json
Authorization: Bearer <token>

{
  "first_name": "Петр",
  "bio": "Senior разработчик"
}
```

### Внутренние роуты

**Расположение**: `src/modules/users/routers/internal.py`

| Метод | Путь | Описание | Auth |
|-------|------|----------|------|
| `GET` | `/internal/users/` | Список с фильтрацией | Service key |
| `POST` | `/internal/users/` | Создание профиля | Service key |
| `GET` | `/internal/users/{profile_id}` | Профиль по ID | Service key |
| `PATCH` | `/internal/users/{profile_id}` | Обновление профиля | Service key |
| `DELETE` | `/internal/users/{profile_id}` | Удаление профиля | Service key |
| `POST` | `/internal/users/{profile_id}/telegram` | Создание Telegram | Service key |

## События шины

### Подписки (входящие события)

#### user.registered
```python
@bus.subscribe(BusTopics.USER_REGISTERED)
async def handle_user_registered(message: dict):
    """
    Обработка регистрации пользователя
    
    - Логирует событие
    - Может создавать профиль автоматически (опционально)
    """
```

**Топик**: `user.registered`

**От кого**: `auth`

**Данные**:
```json
{
  "auth_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com"
}
```

#### user.logged_in
```python
@bus.subscribe(BusTopics.USER_LOGGED_IN)
async def handle_user_logged_in(message: dict):
    """Логирует вход пользователя"""
```

**Топик**: `user.logged_in`

**От кого**: `auth`

### Публикации (исходящие события)

#### ProfileCreated
```python
class ProfileCreated(BaseEvent):
    """Профиль создан"""
    
    profile_id: UUID
    auth_id: UUID
    email: str | None
```

**Топик**: `profile.created`

**Когда публикуется:**
- После создания профиля через `create_user_profile()`

#### ProfileUpdated
```python
class ProfileUpdated(BaseEvent):
    """Профиль обновлён"""
    
    profile_id: UUID
    auth_id: UUID
    updated_fields: list[str]
```

**Топик**: `profile.updated`

**Когда публикуется:**
- После обновления профиля через `update_profile()`

#### ProfileDeleted
```python
class ProfileDeleted(BaseEvent):
    """Профиль удалён"""
    
    profile_id: UUID
    auth_id: UUID
```

**Топик**: `profile.deleted`

**Когда публикуется:**
- После удаления профиля через `delete_profile()`

## DI-зависимости

**Расположение**: `src/modules/users/dependencies.py`

```python
def get_user_repository() -> UserRepository:
    """Фабрика репозитория пользователей"""
    return UserRepository()


def get_telegram_repository() -> TelegramRepository:
    """Фабрика Telegram репозитория"""
    return TelegramRepository()


def get_user_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
    telegram_repo: Annotated[TelegramRepository, Depends(get_telegram_repository)],
) -> UserService:
    """
    Фабрика сервиса
    
    Обратите внимание: сервис получает оба репозитория
    """
    return UserService(
        repository=user_repo,
        telegram_repository=telegram_repo,
        message_bus=get_producer(),
    )
```

## Обработчики шины

**Расположение**: `src/modules/users/handlers.py`

```python
@bus.subscribe(BusTopics.USER_REGISTERED)
async def handle_user_registered(message: dict):
    """
    Обработка регистрации
    
    Логирует событие, может использоваться для:
    - Аудита
    - Автоматического создания профиля
    - Отправки welcome-письма (через notifications)
    """
    logger.info("Новый пользователь: auth_id=%s", message.get("auth_id"))


@bus.subscribe(BusTopics.USER_LOGGED_IN)
async def handle_user_logged_in(message: dict):
    """Логирует вход пользователя"""
    logger.info("Вход пользователя: auth_id=%s", message.get("auth_id"))


@bus.subscribe(BusTopics.PROFILE_CREATED)
async def handle_profile_created(message: dict):
    """Логирует создание профиля"""
    logger.info("Профиль создан: profile_id=%s", message.get("profile_id"))


@bus.subscribe(BusTopics.PROFILE_UPDATED)
async def handle_profile_updated(message: dict):
    """Логирует обновление профиля"""
    logger.info("Профиль обновлён: profile_id=%s", message.get("profile_id"))


@bus.subscribe(BusTopics.PROFILE_DELETED)
async def handle_profile_deleted(message: dict):
    """Логирует удаление профиля"""
    logger.info("Профиль удалён: profile_id=%s", message.get("profile_id"))
```

## Константы

**Расположение**: `src/modules/users/constants.py`

### ERROR_MESSAGES

```python
ERROR_MESSAGES = {
    "profile_exists": "Профиль пользователя уже существует",
    "profile_not_found": "Профиль пользователя не найден",
    "telegram_exists": "Telegram уже привязан к другому пользователю",
    "telegram_not_found": "Telegram-профиль не найден",
}
```

## Взаимосвязи с другими модулями

### Зависит от

| Модуль | Тип | Описание |
|--------|-----|----------|
| `bus` | Шина | Публикация/подписка на события |
| `auth` | События | Подписка на `user.registered`, `user.logged_in` |

### Используется

| Модуль | Тип | Описание |
|--------|-----|----------|
| `notifications` | UsersClient | Резолвинг email по auth_id |
| `job_matcher` | UsersClient | Получение данных пользователя |
| `telegram_clients` | FK | Связь через telegram_id |

## Клиенты (межмодульное взаимодействие)

### UsersClient

**Расположение**: `src/core/clients/users_client.py`

```python
class UsersClient:
    """
    Клиент для межмодульного взаимодействия с users модулем
    
    Новый подход: прямые вызовы через DI, без HTTP
    """
    
    async def resolve_email_by_auth_id(self, auth_id: UUID) -> str | None:
        """
        Получение email по auth_id
        
        Используется в notifications для отправки писем
        """
    
    async def get_user_profile(self, auth_id: UUID) -> UserRead | None:
        """
        Получение профиля пользователя
        
        Используется в job_matcher для получения данных
        """
```

**Использование:**
```python
from src.core.clients import UsersClient

# В сервисе или обработчике
client = UsersClient()
email = await client.resolve_email_by_auth_id(auth_id)
```

## Примеры использования

### Создание профиля после регистрации

```python
async with session.begin():
    profile = await service.create_user_profile(
        session=session,
        auth_id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
        data=UserCreate(
            first_name="Иван",
            last_name="Иванов",
            bio="Разработчик",
        ),
    )
```

### Получение профиля с Telegram

```python
async with session.begin():
    user, telegram = await service.get_profile_with_telegram(
        session=session,
        auth_id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
    )
    
    if telegram:
        print(f"Telegram: @{telegram.telegram_username}")
```

### Привязка Telegram

```python
async with session.begin():
    telegram_profile = await service.create_telegram_profile(
        session=session,
        profile_id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
        data=TelegramCreate(
            telegram_id=123456789,
            telegram_username="ivanov",
            telegram_first_name="Иван",
        ),
    )
```

### Фильтрация пользователей

```python
from datetime import datetime, timedelta

async with session.begin():
    filters = UserFilters(
        search="Иван",
        created_from=datetime.now() - timedelta(days=30),
    )
    
    users = await service.get_users(
        session=session,
        filters=filters,
        skip=0,
        limit=50,
    )
```

## Тестирование

**Расположение тестов**: `tests/modules/users/`

### Фикстуры

```python
@pytest.fixture
def user_service(user_repository, telegram_repository, message_bus):
    return UserService(
        repository=user_repository,
        telegram_repository=telegram_repository,
        message_bus=message_bus,
    )


@pytest.fixture
def user_repository(db_session):
    return UserRepository()


@pytest.fixture
def telegram_repository(db_session):
    return TelegramRepository()
```

### Пример теста

```python
async def test_create_user_profile(db_session, user_service, auth_id):
    data = UserCreate(
        first_name="Иван",
        last_name="Иванов",
        bio="Разработчик",
    )
    
    profile = await user_service.create_user_profile(
        db_session, auth_id, data
    )
    
    assert profile.first_name == "Иван"
    assert profile.auth_id == auth_id
```

## Миграции Alembic

**Файл миграции**: `alembic/versions/XXXX_create_users_tables.py`

```python
def upgrade():
    # Таблица пользователей
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('auth_id', sa.UUID(), nullable=False),
        sa.Column('first_name', sa.String(), nullable=True),
        sa.Column('last_name', sa.String(), nullable=True),
        sa.Column('avatar_url', sa.String(), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('telegram_id', sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_auth_id', 'users', ['auth_id'], unique=True)
    
    # Таблица Telegram
    op.create_table(
        'telegram',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('telegram_id', sa.Integer(), nullable=False),
        sa.Column('telegram_username', sa.String(), nullable=True),
        sa.Column('telegram_first_name', sa.String(), nullable=True),
        sa.Column('telegram_last_name', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['telegram_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
```
