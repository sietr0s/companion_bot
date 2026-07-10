# Модуль AUTH

**Расположение**: `src/modules/auth/`

## Назначение

Управление учётными записями авторизации: регистрация, вход, JWT-токены, смена пароля. Модуль полностью изолирован от профиля пользователя — `auth_id` используется как внешний идентификатор для связи с другими модулями.

## Бизнес-логика

### Основные возможности

- Регистрация нового аккаунта (email/phone/telegram)
- Вход по идентификатору и паролю
- Генерация и проверка JWT-токенов
- Смена пароля
- Удаление аккаунта
- Internal API для создания/обновления аккаунтов (для других модулей)

### Идентификаторы

Поддерживается три типа идентификаторов:
- `EMAIL` — адрес электронной почты
- `PHONE` — номер телефона
- `TELEGRAM` — Telegram ID

## Модели данных

### Auth

```python
class Auth(BaseModel):
    """Модель учётной записи"""
    
    id: UUID                      # Уникальный ID аккаунта
    identifier: str               # Email/phone/telegram (индексировано)
    identifier_type: IdentifierType  # Тип идентификатора
    hashed_password: str          # Хэш пароля (bcrypt)
    role: str                     # Роль пользователя
```

**Индексы:**
- `ix_auth_identifier` — для быстрого поиска при логине

## Репозиторий

### AuthRepository

**Расположение**: `src/modules/auth/repository.py`

```python
class AuthRepository(BaseRepository[Auth]):
    """Репозиторий для работы с учётными записями"""
    
    async def get_by_identifier(
        self, session: AsyncSession, identifier: str
    ) -> Auth | None:
        """Поиск аккаунта по идентификатору (email/phone/telegram)"""
```

**Методы:**
- `get_by_identifier(session, identifier)` — поиск по email/phone/telegram
- Стандартные CRUD методы от `BaseRepository`: `get`, `get_all`, `create`, `update`, `delete`

## Сервис

### AuthService

**Расположение**: `src/modules/auth/service.py`

```python
class AuthService(BaseService[AuthRepository]):
    """Бизнес-логика авторизации"""
```

### Публичные методы

#### register
```python
async def register(
    self, session: AsyncSession, data: AuthCreate
) -> Auth:
    """
    Регистрация нового аккаунта
    
    - Проверяет уникальность идентификатора
    - Хэширует пароль
    - Создаёт аккаунт
    - Публикует событие USER_REGISTERED
    
    Raises:
        ConflictError: Если идентификатор уже занят
    """
```

#### register_and_return_id
```python
async def register_and_return_id(
    self, session: AsyncSession, data: AuthCreate
) -> UUID:
    """
    Регистрация без публикации события (для клиентов)
    
    Возвращает только auth_id нового аккаунта
    """
```

#### login
```python
async def login(
    self, session: AsyncSession, data: LoginRequest
) -> tuple[Auth, str]:
    """
    Вход пользователя
    
    - Проверяет идентификатор и пароль
    - Генерирует JWT-токен
    - Публикует событие USER_LOGGED_IN
    
    Raises:
        UnauthorizedError: Если неверный идентификатор или пароль
    """
```

#### change_password
```python
async def change_password(
    self,
    session: AsyncSession,
    auth_id: UUID,
    current_password: str,
    new_password: str,
) -> None:
    """
    Смена пароля
    
    - Проверяет текущий пароль
    - Обновляет хэш нового пароля
    
    Raises:
        UnauthorizedError: Если неверный текущий пароль
    """
```

#### delete_account
```python
async def delete_account(
    self, session: AsyncSession, auth_id: UUID
) -> None:
    """
    Удаление аккаунта
    
    - Удаляет аккаунт из БД
    - Публикует событие USER_DELETED
    """
```

### Internal методы

#### create_account
```python
async def create_account(
    self, session: AsyncSession, data: AuthCreateInternal
) -> Auth:
    """Internal создание аккаунта (без хэширования пароля)"""
```

#### update_account
```python
async def update_account(
    self,
    session: AsyncSession,
    auth_id: UUID,
    data: AuthUpdate,
) -> Auth:
    """Internal обновление аккаунта"""
```

#### verify_token_internal
```python
async def verify_token_internal(self, token: str) -> UUID:
    """
    Проверка JWT-токена
    
    Returns:
        UUID: auth_id из токена
    
    Raises:
        UnauthorizedError: Если токен невалиден
    """
```

## HTTP API

### Публичные роуты

**Расположение**: `src/modules/auth/routers/public.py`

| Метод | Путь | Описание | Auth |
|-------|------|----------|------|
| `POST` | `/public/auth/register` | Регистрация нового аккаунта | ❌ |
| `POST` | `/public/auth/login` | Вход, получение JWT | ❌ |
| `PATCH` | `/public/auth/me/password` | Смена пароля | ✅ JWT |
| `DELETE` | `/public/auth/me` | Удаление аккаунта | ✅ JWT |

#### Примеры запросов

**Регистрация:**
```bash
POST /public/auth/register
Content-Type: application/json

{
  "identifier": "user@example.com",
  "identifier_type": "EMAIL",
  "password": "SecurePass123!"
}
```

**Ответ:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "identifier": "user@example.com",
  "identifier_type": "EMAIL",
  "role": "user"
}
```

**Вход:**
```bash
POST /public/auth/login
Content-Type: application/json

{
  "identifier": "user@example.com",
  "password": "SecurePass123!"
}
```

**Ответ:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer"
}
```

### Внутренние роуты

**Расположение**: `src/modules/auth/routers/internal.py`

| Метод | Путь | Описание | Auth |
|-------|------|----------|------|
| `POST` | `/internal/auth/` | Создание аккаунта | ❌ |
| `GET` | `/internal/auth/{auth_id}` | Получение аккаунта по ID | ❌ |
| `PATCH` | `/internal/auth/{auth_id}` | Обновление аккаунта | ❌ |
| `DELETE` | `/internal/auth/{auth_id}` | Удаление аккаунта | ❌ |
| `POST` | `/internal/auth/verify` | Проверка JWT-токена | ❌ |

#### Пример проверки токена

**Запрос:**
```bash
POST /internal/auth/verify
Content-Type: application/json

{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Ответ:**
```json
{
  "auth_id": "550e8400-e29b-41d4-a716-446655440000",
  "valid": true
}
```

## События шины

### UserRegistered

**Расположение**: `src/modules/auth/schemas/events.py`

```python
class UserRegistered(BaseEvent):
    """Пользователь зарегистрирован"""
    
    auth_id: UUID
    email: str
```

**Топик**: `user.registered`

**Когда публикуется:**
- После успешной регистрации через `register()`

**Подписчики:**
- `users.handlers` — создание профиля пользователя
- `notifications.handlers` — отправка welcome-письма

### UserLoggedIn

```python
class UserLoggedIn(BaseEvent):
    """Пользователь вошёл"""
    
    auth_id: UUID
    email: str
```

**Топик**: `user.logged_in`

**Когда публикуется:**
- После успешного входа через `login()`

**Подписчики:**
- `users.handlers` — логирование входа

### UserDeleted

```python
class UserDeleted(BaseEvent):
    """Аккаунт удалён"""
    
    auth_id: UUID
```

**Топик**: `user.deleted`

**Когда публикуется:**
- После удаления аккаунта через `delete_account()`

**Подписчики:**
- Нет (событие для будущего расширения)

## DI-зависимости

**Расположение**: `src/modules/auth/dependencies.py`

```python
def get_auth_repository() -> AuthRepository:
    """Фабрика репозитория"""
    return AuthRepository()


def get_auth_service(
    repository: Annotated[AuthRepository, Depends(get_auth_repository)],
    message_bus: Annotated[MessageBus, Depends(get_message_bus)],
) -> AuthService:
    """Фабрика сервиса"""
    return AuthService(repository=repository, message_bus=message_bus)
```

**Использование в роутах:**
```python
@router.post("/register")
async def register(
    data: AuthCreate,
    service: Annotated[AuthService, Depends(get_auth_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Auth:
    return await service.register(session, data)
```

## Константы

**Расположение**: `src/modules/auth/constants.py`

### IdentifierType

```python
class IdentifierType(str, Enum):
    EMAIL = "email"
    PHONE = "phone"
    TELEGRAM = "telegram"
```

### ERROR_MESSAGES

```python
ERROR_MESSAGES = {
    "identifier_exists": "Аккаунт с таким идентификатором уже существует",
    "invalid_credentials": "Неверный идентификатор или пароль",
    "current_password_invalid": "Неверный текущий пароль",
    "account_not_found": "Аккаунт не найден",
}
```

## Взаимосвязи с другими модулями

### Зависит от

| Модуль | Тип | Описание |
|--------|-----|----------|
| `bus` | Шина | Публикация событий о регистрации/входе/удалении |

### Используется

| Модуль | Тип | Описание |
|--------|-----|----------|
| `users` | Подписка | Создание профиля при регистрации |
| `job_matcher` | AuthClient | Проверка токена, получение auth_id |
| `notifications` | Подписка | Отправка welcome-письма |

## Безопасность

### Хэширование пароля

- **Алгоритм**: bcrypt
- **Соль**: Автоматическая генерация при хэшировании
- **Проверка**: `bcrypt.verify(plain_password, hashed_password)`

### JWT-токены

- **Алгоритм**: HS256
- **Время жизни**: Настраивается через `JWT_ACCESS_TOKEN_EXPIRES_MINUTES`
- **Claims**:
  - `sub`: auth_id пользователя
  - `exp`: время истечения
  - `iat`: время выпуска

### Защита роутов

- Публичные роуты (`/public/auth/me/*`) требуют JWT-токен
- Токен передаётся в заголовке `Authorization: Bearer <token>`
- Валидация токена через `get_current_user` зависимость

## Примеры использования

### Регистрация и вход

```python
# Регистрация
async with session.begin():
    auth = await service.register(session, AuthCreate(
        identifier="user@example.com",
        identifier_type=IdentifierType.EMAIL,
        password="SecurePass123!",
    ))
    # auth.id содержит UUID нового аккаунта

# Вход
async with session.begin():
    auth, token = await service.login(session, LoginRequest(
        identifier="user@example.com",
        password="SecurePass123!",
    ))
    # token содержит JWT для последующих запросов
```

### Смена пароля

```python
async with session.begin():
    await service.change_password(
        session=session,
        auth_id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
        current_password="OldPass123!",
        new_password="NewPass456!",
    )
```

### Internal API для других модулей

```python
# Создание аккаунта из другого модуля
async with session.begin():
    auth = await service.create_account(session, AuthCreateInternal(
        identifier="telegram_123456789",
        identifier_type=IdentifierType.TELEGRAM,
        hashed_password="",  # Пустой пароль для Telegram-аккаунтов
        role="user",
    ))
```

## Тестирование

**Расположение тестов**: `tests/modules/auth/`

### Фикстуры

```python
@pytest.fixture
def auth_service(auth_repository, message_bus):
    return AuthService(repository=auth_repository, message_bus=message_bus)


@pytest.fixture
def auth_repository(db_session):
    return AuthRepository()
```

### Пример теста

```python
async def test_register_creates_account(db_session, auth_service):
    data = AuthCreate(
        identifier="test@example.com",
        identifier_type=IdentifierType.EMAIL,
        password="SecurePass123!",
    )
    
    auth = await auth_service.register(db_session, data)
    
    assert auth.identifier == "test@example.com"
    assert auth.hashed_password != "SecurePass123!"
```

## Миграции Alembic

**Файл миграции**: `alembic/versions/XXXX_create_auth_table.py`

```python
def upgrade():
    op.create_table(
        'auth',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('identifier', sa.String(), nullable=False),
        sa.Column('identifier_type', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_auth_identifier', 'auth', ['identifier'], unique=False)
```
