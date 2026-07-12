# Модуль TELEGRAM_CLIENTS

**Расположение**: `src/modules/telegram_clients/`

## Назначение

Управление подключением к Telegram через Telethon: авторизация (SMS/2FA), получение чатов и сообщений, управление настройками чтения. Модуль управляет singleton `TelegramClientManager`.

## Бизнес-логика

### Основные возможности

- Пошаговая авторизация в Telegram (SMS → код → 2FA)
- QR-авторизация в Telegram (альтернатива SMS)
- Подключение аккаунтов по session-файлам
- Отключение аккаунтов
- Получение списка чатов
- Получение сообщений из чатов
- Настройки чтения (какие чаты читать: группы/каналы/личные)
- Whitelist chat_id для фильтрации
- Загрузка медиа из сообщений в модуль `media`

## Модели данных

### TelegramAccount

```python
class TelegramAccount(BaseModel):
    """Telegram-аккаунт пользователя"""
    
    id: UUID                      # Уникальный ID записи
    auth_id: UUID                 # Владелец аккаунта (из auth модуля)
    phone: str                    # Номер телефона
    session_file: str             # Путь к session-файлу
    is_connected: bool            # Статус подключения
    first_name: str | None        # Имя из Telegram
    last_name: str | None         # Фамилия из Telegram
    username: str | None          # Username из Telegram
    telegram_id: int | None       # ID в Telegram
```

**Индексы:**
- `ix_telegram_account_auth_id` — для поиска по владельцу
- `ix_telegram_account_connected` — для поиска подключённых аккаунтов

### TelegramSettings

```python
class TelegramSettings(BaseModel):
    """Настройки чтения Telegram-аккаунта"""
    
    id: UUID                      # Уникальный ID записи
    account_id: UUID              # Связь с TelegramAccount (FK)
    read_groups: bool = True      # Читать групповые чаты
    read_personal: bool = True    # Читать личные сообщения
    read_channels: bool = False   # Читать каналы
    whitelist_chat_ids: list[int] # Whitelist chat_id (JSON)
```

**Индексы:**
- `ix_telegram_settings_account_id` — уникальный индекс на account_id

## Репозитории

### TelegramAccountRepository

**Расположение**: `src/modules/telegram_clients/repository.py`

```python
class TelegramAccountRepository(BaseRepository[TelegramAccount]):
    """Репозиторий для работы с Telegram-аккаунтами"""
    
    async def get_by_auth_id(
        self,
        session: AsyncSession,
        auth_id: UUID,
        filters: TelegramAccountFilters | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[TelegramAccount]:
        """
        Получение аккаунтов пользователя с пагинацией
        
        Фильтры:
        - is_connected: статус подключения
        """
    
    async def get_connected_accounts(
        self, session: AsyncSession
    ) -> list[TelegramAccount]:
        """Получение всех подключённых аккаунтов"""
```

### TelegramSettingsRepository

```python
class TelegramSettingsRepository(BaseRepository[TelegramSettings]):
    """Репозиторий для работы с настройками Telegram"""
    
    async def get_by_account_id(
        self, session: AsyncSession, account_id: UUID
    ) -> TelegramSettings | None:
        """Получение настроек по account_id"""
```

## Сервис

### TelegramClientService

**Расположение**: `src/modules/telegram_clients/service.py`

```python
class TelegramClientService(BaseService[TelegramAccountRepository]):
    """Бизнес-логика управления Telegram-аккаунтами"""
```

### Методы авторизации (пошаговые)

#### request_code (Шаг 1)
```python
async def request_code(
    self, session: AsyncSession, data: PhoneRequest, auth_id: UUID
) -> AuthStep1Response:
    """
    Шаг 1: Отправка SMS с кодом
    
    - Сохраняет phone в состоянии
    - Вызывает TelegramClientManager.send_code()
    - Возвращает статус: CODE_SENT или TWO_FA_REQUIRED
    
    Raises:
        ConflictError: Если телефон уже зарегистрирован
    """
```

#### verify_code (Шаг 2)
```python
async def verify_code(
    self, session: AsyncSession, data: CodeRequest, auth_id: UUID
) -> AuthStep2Response:
    """
    Шаг 2: Ввод кода из SMS
    
    - Вызывает TelegramClientManager.sign_in_with_code()
    - Создаёт TelegramAccount в БД
    - Сохраняет session-файл
    - Публикует событие TG_ACCOUNT_CONNECTED
    
    Raises:
        UnauthorizedError: Если неверный код
    """
```

#### verify_password (Шаг 3)
```python
async def verify_password(
    self, session: AsyncSession, data: PasswordRequest, auth_id: UUID
) -> AuthStep3Response:
    """
    Шаг 3: Ввод 2FA пароля
    
    - Вызывает TelegramClientManager.sign_in_with_password()
    - Создаёт TelegramAccount в БД
    - Публикует событие TG_ACCOUNT_CONNECTED
    
    Raises:
        UnauthorizedError: Если неверный пароль
    """
```

### QR-авторизация (альтернативный метод)

#### start_qr_auth
```python
async def start_qr_auth(
    self, session: AsyncSession, auth_id: UUID
) -> QrStartResponse:
    """
    Шаг 1 QR: Создание QR-сессии

    - Генерирует account_id
    - Создаёт временный Telethon-клиент
    - Запускает qr_login() и фоновый asyncio.Task для ожидания
    - НЕ создаёт запись в БД
    - Возвращает account_id и qr_url для генерации QR-кода

    Запись в БД создаётся только после успешного сканирования QR
    через complete_qr_auth()
    """
```

#### get_qr_status
```python
async def get_qr_status(
    self, account_id: UUID
) -> QrStatusResponse:
    """
    Статус QR-сессии

    Возвращает один из статусов:
    - pending: ожидание сканирования
    - connected: QR отсканирован успешно
    - expired: QR истёк по времени
    - error: ошибка авторизации
    """
```

#### complete_qr_auth
```python
async def complete_qr_auth(
    self, session: AsyncSession, auth_id: UUID, account_id: UUID
) -> TelegramAccount:
    """
    Финализация QR-авторизации

    - Получает данные пользователя из Telegram (get_me)
    - Создаёт TelegramAccount в БД
    - Публикует TgAccountConnected
    """
```

#### cancel_qr_auth
```python
async def cancel_qr_auth(
    self, account_id: UUID
) -> None:
    """Отмена QR-сессии и очистка временных данных"""
```

### Методы управления аккаунтами

#### get_accounts
```python
async def get_accounts(
    self,
    session: AsyncSession,
    auth_id: UUID,
    filters: TelegramAccountFilters,
    skip: int = 0,
    limit: int = 100,
) -> list[TelegramAccount]:
    """Получение списка аккаунтов пользователя с фильтрацией"""
```

#### delete_account
```python
async def delete_account(
    self, session: AsyncSession, account_id: UUID, auth_id: UUID
) -> None:
    """
    Удаление аккаунта
    
    - Отключает аккаунт через TelegramClientManager
    - Удаляет session-файл
    - Удаляет запись из БД
    - Публикует событие TG_ACCOUNT_DISCONNECTED
    
    Raises:
        NotFoundError: Если аккаунт не найден
        ForbiddenError: Если аккаунт не принадлежит пользователю
    """
```

### Методы работы с чатами и сообщениями

#### get_chats
```python
async def get_chats(
    self,
    session: AsyncSession,
    account_id: UUID,
    auth_id: UUID,
    limit: int = 100,
) -> list[ChatRead]:
    """
    Получение списка чатов
    
    Raises:
        NotFoundError: Если аккаунт не найден
        ForbiddenError: Если аккаунт не принадлежит пользователю
    """
```

#### get_messages
```python
async def get_messages(
    self,
    session: AsyncSession,
    account_id: UUID,
    chat_id: int,
    auth_id: UUID,
    limit: int = 50,
    offset_id: int = 0,
) -> list[MessageRead]:
    """
    Получение сообщений из чата
    
    Параметры:
    - offset_id: ID сообщения для пагинации (0 для начала)
    
    Raises:
        NotFoundError: Если аккаунт не найден
        ForbiddenError: Если аккаунт не принадлежит пользователю
    """
```

### Методы управления настройками

#### get_settings
```python
async def get_settings(
    self, session: AsyncSession, account_id: UUID
) -> TelegramSettings | None:
    """Получение настроек аккаунта"""
```

#### update_settings
```python
async def update_settings(
    self,
    session: AsyncSession,
    account_id: UUID,
    data: TelegramSettingsUpdate,
) -> TelegramSettings:
    """Обновление настроек аккаунта"""
```

#### delete_settings
```python
async def delete_settings(
    self, session: AsyncSession, account_id: UUID
) -> None:
    """Удаление настроек аккаунта"""
```

## TelegramClientManager

**Расположение**: `src/modules/telegram_clients/client_manager.py`

### Singleton для управления клиентами

```python
class TelegramClientManager:
    """
    Singleton для управления Telegram клиентами
    
    Не входит в DI-контейнер, управляется в main.py
    """
    
    _clients: dict[UUID, TelegramClient]  # Активные подключения
```

### Методы

```python
async def send_code(self, phone: str, account_id: UUID) -> TgAuthStatus:
    """Отправить SMS с кодом"""

async def sign_in_with_code(
    self, account_id: UUID, code: str
) -> TgAuthStatus:
    """Вход по коду из SMS"""

async def sign_in_with_password(
    self, account_id: UUID, password: str
) -> TgAuthStatus:
    """Вход по 2FA паролю"""

async def connect_account(self, account_id: UUID) -> None:
    """Подключение аккаунта по session-файлу"""

async def disconnect_account(self, account_id: UUID) -> None:
    """Отключение аккаунта"""

async def send_message(
    self, account_id: UUID, chat_id: int, text: str
) -> None:
    """Отправка сообщения"""

async def get_chats(
    self, account_id: UUID, limit: int = 100
) -> list[Dialog]:
    """Получение списка чатов"""

async def get_messages(
    self,
    account_id: UUID,
    chat_id: int,
    limit: int = 50,
    offset_id: int = 0,
) -> list[Message]:
    """Получение сообщений из чата"""

async def get_me(self, account_id: UUID) -> User:
    """Информация о пользователе Telegram"""

async def should_read_message(
    self,
    session: AsyncSession,
    account_id: UUID,
    chat_id: int,
    chat_type: ChatType,
) -> bool:
    """Проверка настроек чтения для данного типа чата"""

async def stop_all(self) -> None:
    """Отключение всех клиентов (при остановке приложения)"""
```

## HTTP API

### Публичные роуты

**Расположение**: `src/modules/telegram_clients/routers/public.py`

| Метод | Путь | Описание | Auth |
|-------|------|----------|------|
| `POST` | `/public/telegram/auth/phone` | Шаг 1: отправка SMS | ✅ JWT |
| `POST` | `/public/telegram/auth/code` | Шаг 2: ввод кода | ✅ JWT |
| `POST` | `/public/telegram/auth/password` | Шаг 3: ввод 2FA | ✅ JWT |
| `GET` | `/public/telegram/` | Список аккаунтов | ✅ JWT |
| `GET` | `/public/telegram/{account_id}` | Детали аккаунта | ✅ JWT |
| `DELETE` | `/public/telegram/{account_id}` | Удаление аккаунта | ✅ JWT |
| `GET` | `/public/telegram/{account_id}/chats` | Список чатов | ✅ JWT |
| `GET` | `/public/telegram/{account_id}/chats/{chat_id}/messages` | Сообщения | ✅ JWT |
| `GET` | `/public/telegram/{account_id}/settings` | Настройки | ✅ JWT |
| `POST` | `/public/telegram/{account_id}/settings` | Создание настроек | ✅ JWT |
| `PUT` | `/public/telegram/{account_id}/settings` | Обновление настроек | ✅ JWT |
| `DELETE` | `/public/telegram/{account_id}/settings` | Удаление настроек | ✅ JWT |
| `POST` | `/public/telegram/auth/qr` | Старт QR-сессии | ✅ JWT |
| `GET` | `/public/telegram/auth/qr/{account_id}/status` | Статус QR-сессии | ✅ JWT |
| `DELETE` | `/public/telegram/auth/qr/{account_id}` | Отмена QR-сессии | ✅ JWT |
| `POST` | `/public/telegram/auth/qr/{account_id}/complete` | Завершение QR-авторизации | ✅ JWT |

#### Примеры запросов

**Шаг 1 - Отправка SMS:**
```bash
POST /public/telegram/auth/phone
Content-Type: application/json
Authorization: Bearer <token>

{
  "phone": "+79991234567"
}
```

**Ответ:**
```json
{
  "status": "CODE_SENT",
  "phone": "+79991234567"
}
```

**Шаг 2 - Ввод кода:**
```bash
POST /public/telegram/auth/code
Content-Type: application/json
Authorization: Bearer <token>

{
  "phone": "+79991234567",
  "code": 12345
}
```

**Ответ:**
```json
{
  "status": "CONNECTED",
  "account_id": "550e8400-e29b-41d4-a716-446655440000",
  "telegram_id": 123456789,
  "username": "ivanov"
}
```

**Получение чатов:**
```bash
GET /public/telegram/{account_id}/chats?limit=50
Authorization: Bearer <token>
```

**Ответ:**
```json
[
  {
    "chat_id": 123456789,
    "title": "Рабочий чат",
    "type": "GROUP",
    "unread_count": 5
  },
  {
    "chat_id": 987654321,
    "title": "Иван Иванов",
    "type": "PRIVATE",
    "unread_count": 0
  }
]
```

## События шины

### Публикации (исходящие события)

#### TgMessageReceived
```python
class TgMessageReceived(BaseEvent):
    """Входящее сообщение из Telegram"""
    
    account_id: UUID
    chat_id: int
    message_id: int
    text: str | None
    from_id: int | None
    chat_type: ChatType
    media: list[MediaItem] | None
```

**Топик**: `tg.message.received`

**Когда публикуется:**
- При получении нового сообщения из Telegram

**Подписчики:**
- `job_matcher.handlers` — сохранение вакансий
- `media.handlers` — загрузка медиа

#### TgMessageSend
```python
class TgMessageSend(BaseEvent):
    """Запрос на отправку сообщения"""
    
    account_id: UUID
    chat_id: int
    text: str
```

**Топик**: `tg.message.send`

**Когда публикуется:**
- Для отправки сообщения через Telegram-аккаунт

**Подписчики:**
- `telegram_clients.handlers` — отправка сообщения

#### TgAccountConnected
```python
class TgAccountConnected(BaseEvent):
    """Telegram-аккаунт подключён"""
    
    account_id: UUID
    auth_id: UUID
    telegram_id: int
```

**Топик**: `tg.account.connected`

**Когда публикуется:**
- После успешной авторизации в Telegram

#### TgAccountDisconnected
```python
class TgAccountDisconnected(BaseEvent):
    """Telegram-аккаунт отключён"""
    
    account_id: UUID
    auth_id: UUID
```

**Топик**: `tg.account.disconnected`

**Когда публикуется:**
- После удаления аккаунта

## Обработчики шины

**Расположение**: `src/modules/telegram_clients/handlers.py`

```python
@bus.subscribe(BusTopics.TG_MESSAGE_SEND)
async def handle_send_message(message: dict):
    """
    Отправка сообщения через Telegram-аккаунт
    
    - Находит аккаунт по account_id
    - Отправляет сообщение через TelegramClientManager
    """
    account_id = uuid.UUID(message["account_id"])
    chat_id = message["chat_id"]
    text = message["text"]
    
    await manager.send_message(account_id, chat_id, text)


@bus.subscribe(BusTopics.TG_MESSAGE_RECEIVED)
async def handle_message_received(message: dict):
    """
    Загрузка медиа из входящих сообщений
    
    - Проверяет наличие медиа в сообщении
    - Загружает медиа через MediaClient
    """
    media_list = message.get("media", [])
    if media_list:
        await media_client.upload_media_list(media_list)
```

## Константы

**Расположение**: `src/modules/telegram_clients/constants.py`

### TgAuthStatus

```python
class TgAuthStatus(str, Enum):
    CODE_SENT = "CODE_SENT"           # Код отправлен
    CONNECTED = "CONNECTED"           # Успешное подключение
    TWO_FA_REQUIRED = "TWO_FA_REQUIRED"  # Требуется 2FA пароль
```

### ChatType

```python
class ChatType(str, Enum):
    PRIVATE = "private"        # Личный чат
    GROUP = "group"            # Группа
    CHANNEL = "channel"        # Канал
    SUPERGROUP = "supergroup"  # Супергруппа
```

### MediaType

```python
class MediaType(str, Enum):
    PHOTO = "photo"           # Фотография
    VIDEO = "video"           # Видео
    VOICE = "voice"           # Голосовое
    DOCUMENT = "document"     # Документ
    AUDIO = "audio"           # Аудио
```

### ERROR_MESSAGES

```python
ERROR_MESSAGES = {
    "phone_exists": "Этот телефон уже зарегистрирован",
    "invalid_code": "Неверный код подтверждения",
    "invalid_password": "Неверный 2FA пароль",
    "account_not_found": "Telegram-аккаунт не найден",
    "account_not_connected": "Telegram-аккаунт не подключён",
    "forbidden": "Доступ запрещён",
    "settings_exist": "Настройки уже существуют",
    "settings_not_found": "Настройки не найдены",
}
```

## DI-зависимости

**Расположение**: `src/modules/telegram_clients/dependencies.py`

```python
def get_telegram_account_repository() -> TelegramAccountRepository:
    """Фабрика репозитория аккаунтов"""
    return TelegramAccountRepository()


def get_telegram_settings_repository() -> TelegramSettingsRepository:
    """Фабрика репозитория настроек"""
    return TelegramSettingsRepository()


def get_client_manager() -> TelegramClientManager:
    """
    Фабрика TelegramClientManager
    
    Возвращает глобальный singleton
    """
    return TelegramClientManager.get_instance()


def get_telegram_client_service(
    repo: Annotated[TelegramAccountRepository, Depends(get_telegram_account_repository)],
    message_bus: Annotated[MessageBus, Depends(get_message_bus)],
    manager: Annotated[TelegramClientManager, Depends(get_client_manager)],
) -> TelegramClientService:
    """Фабрика сервиса"""
    return TelegramClientService(
        repository=repo,
        message_bus=message_bus,
        manager=manager,
    )


def get_telegram_settings_service(
    account_repo: Annotated[TelegramAccountRepository, Depends(get_telegram_account_repository)],
    settings_repo: Annotated[TelegramSettingsRepository, Depends(get_telegram_settings_repository)],
    message_bus: Annotated[MessageBus, Depends(get_message_bus)],
    manager: Annotated[TelegramClientManager, Depends(get_client_manager)],
) -> TelegramClientService:
    """Фабрика сервиса для работы с настройками"""
    return TelegramClientService(
        repository=account_repo,
        settings_repository=settings_repo,
        message_bus=message_bus,
        manager=manager,
    )
```

## Взаимосвязи с другими модулями

### Зависит от

| Модуль | Тип | Описание |
|--------|-----|----------|
| `bus` | Шина | Публикация/подписка на события |
| `media` | MediaClient | Загрузка медиа из сообщений |

### Используется

| Модуль | Тип | Описание |
|--------|-----|----------|
| `job_matcher` | Подписка | Получение вакансий из Telegram |
| `job_bot` | Подписка | Отправка сообщений через бота |

## Session-файлы

### Хранение

Session-файлы хранятся в директории `sessions/`:
- Путь: `sessions/{auth_id}_{telegram_id}.session`
- Маунтится в Docker: `./sessions:/app/sessions`

### Структура session-файла

Telethon создаёт бинарные session-файлы, содержащие:
- DC ID и IP сервера
- Auth key для шифрования
- Session data (пользователи, чаты, кэш)

## Примеры использования

### Пошаговая авторизация

```python
# Шаг 1: Отправка SMS
step1 = await service.request_code(
    session=session,
    data=PhoneRequest(phone="+79991234567"),
    auth_id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
)
# step1.status = "CODE_SENT"

# Шаг 2: Ввод кода
step2 = await service.verify_code(
    session=session,
    data=CodeRequest(phone="+79991234567", code=12345),
    auth_id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
)
# step2.status = "CONNECTED"
# step2.account_id = UUID(...)

# Если требуется 2FA:
if step1.status == "TWO_FA_REQUIRED":
    step3 = await service.verify_password(
        session=session,
        data=PasswordRequest(phone="+79991234567", password="mypassword"),
        auth_id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
    )
```

### Получение сообщений

```python
# Получение последних 50 сообщений из чата
messages = await service.get_messages(
    session=session,
    account_id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
    chat_id=123456789,
    auth_id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
    limit=50,
)

for msg in messages:
    print(f"[{msg.date}] {msg.text}")
```

### Настройка фильтров чтения

```python
# Создание настроек с whitelist
settings = await service.update_settings(
    session=session,
    account_id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
    data=TelegramSettingsUpdate(
        read_groups=True,
        read_personal=False,
        read_channels=False,
        whitelist_chat_ids=[123456789, 987654321],
    ),
)
```

## Тестирование

**Расположение тестов**: `tests/modules/telegram_clients/`

### Фикстуры

```python
@pytest.fixture
def telegram_client_service(account_repo, settings_repo, message_bus, manager):
    return TelegramClientService(
        repository=account_repo,
        settings_repository=settings_repo,
        message_bus=message_bus,
        manager=manager,
    )


@pytest.fixture
def telegram_client_manager():
    return TelegramClientManager.get_instance()
```

## Миграции Alembic

**Файл миграции**: `alembic/versions/XXXX_create_telegram_tables.py`

```python
def upgrade():
    # Telegram аккаунты
    op.create_table(
        'telegram_accounts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('auth_id', sa.UUID(), nullable=False),
        sa.Column('phone', sa.String(), nullable=False),
        sa.Column('session_file', sa.String(), nullable=False),
        sa.Column('is_connected', sa.Boolean(), nullable=False),
        sa.Column('first_name', sa.String(), nullable=True),
        sa.Column('last_name', sa.String(), nullable=True),
        sa.Column('username', sa.String(), nullable=True),
        sa.Column('telegram_id', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_telegram_account_auth_id', 'telegram_accounts', ['auth_id'])
    op.create_index('ix_telegram_account_connected', 'telegram_accounts', ['is_connected'])
    
    # Настройки Telegram
    op.create_table(
        'telegram_settings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('account_id', sa.UUID(), nullable=False),
        sa.Column('read_groups', sa.Boolean(), nullable=False),
        sa.Column('read_personal', sa.Boolean(), nullable=False),
        sa.Column('read_channels', sa.Boolean(), nullable=False),
        sa.Column('whitelist_chat_ids', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['telegram_accounts.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_telegram_settings_account_id', 'telegram_settings', ['account_id'], unique=True)
```
