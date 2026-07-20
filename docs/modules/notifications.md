# Модуль NOTIFICATIONS

**Расположение**: `src/modules/notifications/`

## Назначение

Отправка уведомлений (email/Telegram) через шаблоны Jinja2. Поддержка хранения шаблонов в БД и файловой системе. Логирование всех отправок.

## Бизнес-логика

### Основные возможности

- Создание, чтение, обновление, удаление шаблонов уведомлений
- Отправка уведомлений через шину сообщений
- Поддержка каналов email и Telegram (sms зарезервирован)
- Рендеринг шаблонов Jinja2
- Логирование всех отправок
- Поиск шаблонов (БД → файлы)
- История уведомлений по пользователям

## Модели данных

### NotificationTemplate

```python
class NotificationTemplate(BaseModel):
    """Шаблон уведомления"""
    
    id: UUID                      # Уникальный ID шаблона
    name: str                     # Уникальное имя шаблона
    channel: NotificationChannel  # Канал (email/sms)
    subject_template: str | None  # Шаблон темы (для email)
    body_template: str            # Шаблон тела (Jinja2)
    is_active: bool = True        # Статус шаблона
```

**Индексы:**
- `ix_notification_template_name_channel` — уникальный индекс на (name, channel)

### NotificationLog

```python
class NotificationLog(BaseModel):
    """Лог отправки уведомления"""
    
    id: UUID                      # Уникальный ID записи
    auth_id: UUID                 # Получатель (из auth модуля)
    channel: NotificationChannel  # Канал отправки
    template_name: str            # Имя использованного шаблона
    recipient: str                # Получатель (email/phone)
    subject: str | None           # Тема (для email)
    body: str                     # Тело уведомления
    status: NotificationStatus    # Статус (pending/sent/failed)
    error_message: str | None     # Сообщение об ошибке
    sent_at: datetime | None      # Дата отправки
```

**Индексы:**
- `ix_notification_log_auth_id` — для поиска по пользователю
- `ix_notification_log_status` — для фильтрации по статусу
- `ix_notification_log_sent_at` — для сортировки по дате

## Репозитории

### NotificationTemplateRepository

**Расположение**: `src/modules/notifications/repository.py`

```python
class NotificationTemplateRepository(BaseRepository[NotificationTemplate]):
    """Репозиторий для работы с шаблонами уведомлений"""
    
    async def get_by_name(
        self,
        session: AsyncSession,
        name: str,
        channel: NotificationChannel,
    ) -> NotificationTemplate | None:
        """
        Поиск шаблона по имени и каналу
        
        Используется при отправке уведомлений
        """
```

### NotificationLogRepository

```python
class NotificationLogRepository(BaseRepository[NotificationLog]):
    """Репозиторий для работы с логами уведомлений"""
    
    async def get_by_auth_id(
        self,
        session: AsyncSession,
        auth_id: UUID,
        limit: int = 100,
    ) -> list[NotificationLog]:
        """Получение истории уведомлений пользователя"""
```

## Сервис

### NotificationService

**Расположение**: `src/modules/notifications/service.py`

```python
class NotificationService(BaseService[NotificationTemplateRepository, NotificationTemplate]):
    """Бизнес-логика управления уведомлениями"""
```

### Методы управления шаблонами

#### create_template
```python
async def create_template(
    self, session: AsyncSession, data: TemplateCreate
) -> NotificationTemplate:
    """
    Создание шаблона уведомления
    
    Raises:
        ConflictError: Если шаблон с таким именем уже существует
    """
```

#### get_template
```python
async def get_template(
    self, session: AsyncSession, template_id: UUID
) -> NotificationTemplate:
    """
    Получение шаблона по ID
    
    Raises:
        NotFoundError: Если шаблон не найден
    """
```

#### get_templates
```python
async def get_templates(
    self,
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    filters: TemplateFilters | None = None,
) -> list[NotificationTemplate]:
    """
    Получение списка шаблонов с фильтрацией
    
    Фильтры:
    - channel: фильтр по каналу
    - is_active: фильтр по статусу
    - search: поиск по имени
    """
```

#### update_template
```python
async def update_template(
    self,
    session: AsyncSession,
    template_id: UUID,
    data: TemplateUpdate,
) -> NotificationTemplate:
    """
    Обновление шаблона
    
    Raises:
        NotFoundError: Если шаблон не найден
    """
```

#### delete_template
```python
async def delete_template(
    self, session: AsyncSession, template_id: UUID
) -> None:
    """
    Удаление шаблона
    
    Raises:
        NotFoundError: Если шаблон не найден
    """
```

### Методы работы с историей

#### get_history
```python
async def get_history(
    self,
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    filters: NotificationLogFilters | None = None,
) -> list[NotificationLog]:
    """
    Получение истории уведомлений с фильтрацией
    
    Фильтры:
    - auth_id: фильтр по пользователю
    - channel: фильтр по каналу
    - status: фильтр по статусу
    - sent_from: дата отправки
    - sent_to: дата отправки
    """
```

### Метод отправки уведомлений

#### send_notification
```python
async def send_notification(
    self,
    session: AsyncSession,
    auth_id: UUID,
    template_name: str,
    channel: NotificationChannel,
    body: dict,
    recipient: str | None = None,
) -> NotificationLog:
    """
    Отправка уведомления
    
    Параметры:
    - auth_id: ID пользователя в auth модуле
    - template_name: Имя шаблона
    - channel: Канал отправки (email/sms)
    - body: Контекст для рендеринга шаблона
    - recipient: Получатель (email/phone). Если None, резолвится через UsersClient
    
    Процесс:
    1. Находит шаблон по имени и каналу
    2. Рендерит шаблон через Jinja2
    3. Резолвит recipient через UsersClient (если не указан)
    4. Отправляет через NotificationProvider
    5. Логирует результат
    
    Returns:
        NotificationLog: Запись в логе
    
    Raises:
        NotFoundError: Если шаблон не найден
    """
```

## Template Engine

**Расположение**: `src/modules/notifications/template_engine.py`

### find_template
```python
async def find_template(
    session: AsyncSession,
    name: str,
    channel: NotificationChannel,
) -> NotificationTemplate:
    """
    Поиск шаблона (БД → файлы)
    
    Алгоритм:
    1. Ищет шаблон в БД
    2. Если не найден, ищет файл в templates/{channel}/{name}.jinja
    3. Если найден файл, загружает и кэширует в БД
    
    Raises:
        NotFoundError: Если шаблон не найден нигде
    """
```

### render
```python
def render(template_str: str, context: dict) -> str:
    """
    Рендеринг Jinja2 шаблона
    
    Параметры:
    - template_str: Строка шаблона
    - context: Словарь переменных для подстановки
    
    Returns:
        str: Отрендеренный шаблон
    
    Пример:
    >>> render("Привет, {{ name }}!", {"name": "Иван"})
    "Привет, Иван!"
    """
```

## Обработчики шины

**Расположение**: `src/modules/notifications/handlers.py`

### handle_notification_send
```python
@bus.subscribe(BusTopics.NOTIFICATION_SEND)
async def handle_notification_send(message: dict):
    """
    Отправка уведомления по событию
    
    - Получает данные из события
    - Резолвит email через UsersClient
    - Рендерит шаблон
    - Отправляет через SmtpProvider
    - Логирует результат
    
    Пример данных:
    {
      "auth_id": "UUID",
      "template_name": "welcome_email",
      "channel": "email",
      "body": {"user_name": "Иван"},
      "recipient": null
    }
    """
```

## HTTP API

### Публичные роуты

**Расположение**: `src/modules/notifications/routers/public.py`

| Метод | Путь | Описание | Auth |
|-------|------|----------|------|
| `POST` | `/public/notifications/templates/` | Создание шаблона | ✅ Admin |
| `GET` | `/public/notifications/templates/` | Список шаблонов | ✅ Admin |
| `GET` | `/public/notifications/templates/{template_id}` | Шаблон по ID | ✅ Admin |
| `PATCH` | `/public/notifications/templates/{template_id}` | Обновление шаблона | ✅ Admin |
| `DELETE` | `/public/notifications/templates/{template_id}` | Удаление шаблона | ✅ Admin |
| `GET` | `/public/notifications/history/` | История уведомлений | ✅ Admin |
| `GET` | `/public/notifications/history/{log_id}` | Лог по ID | ✅ Admin |

#### Примеры запросов

**Создание шаблона:**
```bash
POST /public/notifications/templates/
Content-Type: application/json
Authorization: Bearer <admin_token>

{
  "name": "welcome_email",
  "channel": "email",
  "subject_template": "Добро пожаловать, {{ user_name }}!",
  "body_template": "Привет, {{ user_name }}!\n\nРады видеть вас в нашем сервисе."
}
```

**Ответ:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "welcome_email",
  "channel": "email",
  "subject_template": "Добро пожаловать, {{ user_name }}!",
  "body_template": "Привет, {{ user_name }}!\n\nРады видеть вас в нашем сервисе.",
  "is_active": true
}
```

**Получение истории:**
```bash
GET /public/notifications/history/?auth_id=UUID&limit=50
Authorization: Bearer <admin_token>
```

### Внутренние роуты

**Расположение**: `src/modules/notifications/routers/internal.py`

| Метод | Путь | Описание | Auth |
|-------|------|----------|------|
| `POST` | `/internal/notifications/send` | Отправка уведомления | Service key |
| `POST` | `/internal/notifications/templates/{template_id}/render` | Тестовый рендер | Service key |

#### Пример отправки уведомления

```bash
POST /internal/notifications/send
Content-Type: application/json

{
  "auth_id": "550e8400-e29b-41d4-a716-446655440000",
  "template_name": "welcome_email",
  "channel": "email",
  "body": {
    "user_name": "Иван"
  }
}
```

## События шины

### Подписки (входящие)

#### notification.send
```python
class NotificationSend(BaseEvent):
    """Запрос на отправку уведомления"""
    
    auth_id: UUID
    template_name: str
    channel: str
    body: dict
    recipient: str | None
```

**Топик**: `notification.send`

**Когда публикуется:**
- Для отправки уведомления пользователю

**От кого:**
- `job_matcher` — уведомления о новых вакансиях
- `auth` — welcome-письма (потенциально)

**Подписчики:**
- `notifications.handlers` — отправка уведомления

## Провайдеры уведомлений

### NotificationProvider (Protocol)

**Расположение**: `src/modules/notifications/providers/base.py`

```python
class NotificationProvider(Protocol):
    """Protocol для провайдера уведомлений"""
    
    async def send(
        self, to: str, subject: str, body: str
    ) -> None:
        """
        Отправка уведомления
        
        Параметры:
        - to: Получатель (email/phone)
        - subject: Тема (для email)
        - body: Тело уведомления
        """
    
    async def start(self) -> None:
        """Инициализация провайдера"""
    
    async def stop(self) -> None:
        """Остановка провайдера"""
```

### SmtpProvider

**Расположение**: `src/modules/notifications/providers/smtp.py`

```python
class SmtpProvider(NotificationProvider):
    """
    SMTP-провайдер для отправки email
    
    Использует aiosmtplib для асинхронной отправки
    """
```

#### Конфигурация

```python
def __init__(
    self,
    host: str,
    port: int,
    username: str,
    password: str,
    from_email: str,
    use_tls: bool = True,
):
    self.host = host
    self.port = port
    self.username = username
    self.password = password
    self.from_email = from_email
    self.use_tls = use_tls
```

#### Метод send

```python
async def send(
    self, to: str, subject: str, body: str
) -> None:
    """
    Отправка email через SMTP
    
    - Создаёт MIME-сообщение
    - Подключается к SMTP-серверу
    - Отправляет сообщение
    """
```

## DI-зависимости

**Расположение**: `src/modules/notifications/dependencies.py`

```python
def get_notification_template_repository() -> NotificationTemplateRepository:
    """Фабрика репозитория шаблонов"""
    return NotificationTemplateRepository()


def get_notification_log_repository() -> NotificationLogRepository:
    """Фабрика репозитория логов"""
    return NotificationLogRepository()


def get_notification_provider() -> NotificationProvider:
    """
    Фабрика провайдера уведомлений
    
    Возвращает SmtpProvider по умолчанию
    """
    return SmtpProvider(
        host=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USERNAME,
        password=settings.SMTP_PASSWORD,
        from_email=settings.SMTP_FROM_EMAIL,
    )


def get_notification_service(
    template_repo: Annotated[NotificationTemplateRepository, Depends(get_notification_template_repository)],
    log_repo: Annotated[NotificationLogRepository, Depends(get_notification_log_repository)],
    provider: Annotated[NotificationProvider, Depends(get_notification_provider)],
) -> NotificationService:
    """Фабрика сервиса"""
    return NotificationService(
        repository=template_repo,
        log_repository=log_repo,
        provider=provider,
    )


def get_notification_service_factory() -> NotificationService:
    """Создать сервис для обработчика шины."""
    return NotificationService(
        template_repo=NotificationTemplateRepository(),
        log_repo=NotificationLogRepository(),
        provider=SmtpProvider(),
    )
    return factory
```

## Константы

**Расположение**: `src/modules/notifications/constants.py`

### NotificationChannel

```python
class NotificationChannel(str, Enum):
    EMAIL = "email"  # Email уведомления
    SMS = "sms"      # SMS уведомления
    TELEGRAM = "telegram"  # Сообщения через Telegram-бота
```

### NotificationStatus

```python
class NotificationStatus(str, Enum):
    PENDING = "pending"    # Ожидает отправки
    SENT = "sent"          # Успешно отправлено
    FAILED = "failed"      # Ошибка отправки
```

### ERROR_MESSAGES

```python
ERROR_MESSAGES = {
    "template_not_found": "Шаблон уведомления не найден",
    "template_inactive": "Шаблон не активен",
    "recipient_not_found": "Получатель не найден",
    "send_failed": "Ошибка отправки уведомления",
    "smtp_error": "Ошибка SMTP-сервера",
}
```

### Шаблоны по умолчанию

**Расположение**: `templates/email/`

```
templates/
├── email/
│   ├── welcome_email.jinja
│   ├── new_job_offer.jinja
│   └── password_reset.jinja
└── sms/
    └── verification_code.jinja
```

#### Пример шаблона: welcome_email.jinja

```jinja2
Добро пожаловать, {{ user_name }}!

Рады видеть вас в нашем сервисе.

Ваш email: {{ email }}
Дата регистрации: {{ registration_date }}

С уважением,
Команда сервиса
```

## Взаимосвязи с другими модулями

### Зависит от

| Модуль | Тип | Описание |
|--------|-----|----------|
| `bus` | Шина | Подписка на события отправки |
| `users` | UsersClient | Резолвинг email по auth_id |

### Используется

| Модуль | Тип | Описание |
|--------|-----|----------|
| `job_matcher` | Подписка | Отправка уведомлений о вакансиях |
| `auth` | События | Welcome-письма (потенциально) |

## Конфигурация

### Переменные окружения

```bash
# SMTP настройки
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM_EMAIL=noreply@example.com
SMTP_USE_TLS=true

# Настройки уведомлений
NOTIFICATION_DEFAULT_CHANNEL=email
NOTIFICATION_LOG_RETENTION_DAYS=90
```

## Примеры использования

### Создание шаблона

```python
async with session.begin():
    template = await service.create_template(
        session=session,
        data=TemplateCreate(
            name="new_job_offer",
            channel=NotificationChannel.EMAIL,
            subject_template="Новая вакансия: {{ title }}",
            body_template="""
Добрый день, {{ user_name }}!

Нашлась вакансия по вашему запросу:

**{{ title }}**
Зарплата: {{ salary }}
Локация: {{ location }}

{{ description }}

#tags: {{ tags }}
            """.strip(),
        ),
    )
```

### Отправка уведомления через шину

```python
# В job_matcher/handlers.py
await message_bus.publish(
    BusTopics.NOTIFICATION_SEND,
    NotificationSend(
        auth_id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
        template_name="new_job_offer",
        channel=NotificationChannel.EMAIL,
        body={
            "user_name": "Иван",
            "title": "Python разработчик",
            "salary": "100000-200000 ₽",
            "location": "Москва",
            "description": "Ищем Python разработчика...",
            "tags": "python, backend, fastapi",
        },
        recipient=None,  # Будет зарезолвлен через UsersClient
    ).to_bus_dict(),
)
```

### Получение истории уведомлений

```python
async with session.begin():
    logs = await service.get_history(
        session=session,
        filters=NotificationLogFilters(
            auth_id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
            status=NotificationStatus.SENT,
            sent_from=datetime.now() - timedelta(days=7),
        ),
        skip=0,
        limit=50,
    )
    
    for log in logs:
        print(f"[{log.sent_at}] {log.template_name} -> {log.recipient}")
```

## Тестирование

**Расположение тестов**: `tests/modules/notifications/`

### Фикстуры

```python
@pytest.fixture
def notification_service(template_repo, log_repo, provider):
    return NotificationService(
        repository=template_repo,
        log_repository=log_repo,
        provider=provider,
    )


@pytest.fixture
def smtp_provider():
    return SmtpProvider(
        host="localhost",
        port=1025,  # Mailhog для тестов
        username="",
        password="",
        from_email="test@example.com",
    )
```

### Пример теста

```python
async def test_send_notification(db_session, notification_service, auth_id):
    log = await notification_service.send_notification(
        session=db_session,
        auth_id=auth_id,
        template_name="welcome_email",
        channel=NotificationChannel.EMAIL,
        body={"user_name": "Иван"},
        recipient="test@example.com",
    )
    
    assert log.status == NotificationStatus.SENT
    assert log.recipient == "test@example.com"
```

## Миграции Alembic

**Файл миграции**: `alembic/versions/XXXX_create_notifications_tables.py`

```python
def upgrade():
    # Шаблоны уведомлений
    op.create_table(
        'notification_templates',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('channel', sa.String(), nullable=False),
        sa.Column('subject_template', sa.Text(), nullable=True),
        sa.Column('body_template', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_notification_template_name_channel', 'notification_templates', ['name', 'channel'], unique=True)
    
    # Логи уведомлений
    op.create_table(
        'notification_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('auth_id', sa.UUID(), nullable=False),
        sa.Column('channel', sa.String(), nullable=False),
        sa.Column('template_name', sa.String(), nullable=False),
        sa.Column('recipient', sa.String(), nullable=False),
        sa.Column('subject', sa.String(), nullable=True),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_notification_log_auth_id', 'notification_logs', ['auth_id'])
    op.create_index('ix_notification_log_status', 'notification_logs', ['status'])
    op.create_index('ix_notification_log_sent_at', 'notification_logs', ['sent_at'])
```

## Дополнительные материалы

- [Jinja2 документация](https://jinja.palletsprojects.com/)
- [aiosmtplib документация](https://aiosmtplib.readthedocs.io/)
- [job_matcher.md](job_matcher.md) — отправка уведомлений о вакансиях
