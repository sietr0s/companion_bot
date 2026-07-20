# Модуль JOB_MATCHER

**Расположение**: `src/modules/job_matcher/`

## Назначение

Бизнес-логика подбора вакансий: сохранение вакансий из Telegram, классификация, поиск подходящих подписок, отправка уведомлений.

## Бизнес-логика

### Основные возможности

- Сохранение вакансий из Telegram-сообщений
- Отправка вакансий на классификацию
- Обновление категорий вакансий
- Обработка команд бота (/start, /subscribe)
- Создание и управление подписками
- Поиск подходящих вакансий для пользователей
- Отправка уведомлений о новых вакансиях

## Модели данных

### Subscription

```python
class Subscription(BaseModel):
    """Подписка пользователя на вакансии"""
    
    id: UUID                      # Уникальный ID подписки
    auth_id: UUID                 # Владелец подписки (из auth модуля)
    keywords: list[str]           # Ключевые слова (JSON)
    category_ids: list[UUID]      # Категории (JSON)
    min_salary: int | None        # Минимальная зарплата
    max_salary: int | None        # Максимальная зарплата
    locations: list[str]          # Локации (JSON)
    is_active: bool = True        # Статус подписки
```

**Индексы:**
- `ix_subscription_auth_id` — для поиска по владельцу
- `ix_subscription_is_active` — для фильтрации активных

### JobOffer

```python
class JobOffer(BaseModel):
    """Вакансия"""
    
    id: UUID                      # Уникальный ID вакансии
    title: str                    # Заголовок
    description: str              # Описание
    tags: list[str]               # Теги (JSON)
    salary_from: int | None       # Зарплата от
    salary_to: int | None         # Зарплата до
    location: str | None          # Локация
    source_chat_id: int           # Источник: chat_id
    source_message_id: int        # Источник: message_id
    telegram_sender_id: int | None
    telegram_username: str | None
    telegram_first_name: str | None
    telegram_last_name: str | None
    category_ids: list[UUID]      # Категории (JSON)
    created_at: datetime          # Дата создания
```

**Индексы:**
- `ix_job_offer_source` — уникальный индекс на (source_chat_id, source_message_id)
- `ix_job_offer_created_at` — для сортировки по дате

## Репозитории

### SubscriptionRepository

**Расположение**: `src/modules/job_matcher/repository.py`

```python
class SubscriptionRepository(BaseRepository[Subscription]):
    """Репозиторий для работы с подписками"""
    
    async def get_by_auth_id(
        self, session: AsyncSession, auth_id: UUID
    ) -> Subscription | None:
        """Получение подписки пользователя"""
    
    async def find_matching(
        self,
        session: AsyncSession,
        category_ids: list[UUID],
        tags: list[str],
        salary_min: int | None,
        salary_max: int | None,
        location: str | None,
    ) -> list[Subscription]:
        """
        Поиск подходящих подписок для вакансии
        
        Критерии совпадения:
        - category_ids пересекаются
        - keywords пересекаются с tags
        - salary в диапазоне
        - location совпадает или пустая
        """
```

### JobOfferRepository

```python
class JobOfferRepository(BaseRepository[JobOffer]):
    """Репозиторий для работы с вакансиями"""
    
    async def get_by_source(
        self,
        session: AsyncSession,
        source_chat_id: int,
        source_message_id: int,
    ) -> JobOffer | None:
        """Поиск вакансии по источнику (chat_id, message_id)"""
```

## Сервисы

Сервисы расположены в `src/modules/job_matcher/services/` и разделены по ответственности:

- `JobOfferService` — сохранение, классификация и рассылка вакансий;
- `SubscriptionService` — чтение подписок, пагинация и выбор категорий;
- `JobMatcherUserService` — регистрация через `/start` и каскадное удаление subscription, user и auth.

Общего монолитного фасада нет: handlers и routers получают только необходимый сервис.

### Методы

#### save_job_offer
```python
async def save_job_offer(
    self,
    session: AsyncSession,
    text: str,
    chat_id: int,
    message_id: int,
    sender: dict,
) -> JobOffer:
    """
    Сохранение вакансии из Telegram-сообщения
    
    - Парсит текст сообщения
    - Извлекает зарплату, локацию, теги
    - Сохраняет в БД
    - Отправляет на классификацию
    
    Returns:
        JobOffer: Сохранённая вакансия
    """
```

#### send_for_classification
```python
async def send_for_classification(
    self, job_offer_id: UUID, text: str
) -> None:
    """
    Отправка вакансии на классификацию
    
    - Публикует событие text.classify.request
    
    Raises:
        NotFoundError: Если вакансия не найдена
    """
```

#### update_job_offer_categories
```python
async def update_job_offer_categories(
    self,
    session: AsyncSession,
    job_offer_id: UUID,
    category_ids: list[UUID],
) -> None:
    """
    Обновление категорий вакансии
    
    - Обновляет category_ids
    - Публикует событие job.offer.classified
    
    Raises:
        NotFoundError: Если вакансия не найдена
    """
```

#### handle_start
```python
async def handle_start(
    self,
    session: AsyncSession,
    chat_id: int,
    telegram_user: TelegramUserInfo,
) -> None:
    """
    Обработка команды /start
    
    - Регистрирует Auth по telegram_user.telegram_id
    - Создаёт User с именем и фамилией
    - Создаёт и привязывает Telegram-профиль
    - Отправляет приветственное сообщение
    
    Raises:
        ConflictError: Если пользователь уже зарегистрирован
    """
```

#### handle_subscribe
```python
async def handle_subscribe(
    self,
    session: AsyncSession,
    chat_id: int,
    telegram_id: int,
) -> None:
    """
    Обработка команды /subscribe
    
    - Получает страницу активных категорий classifier (по 5 элементов)
    - Отправляет inline-клавиатуру выбора с кнопками «Назад» и «Вперёд»
    - Не создаёт подписку до выбора пользователем
    """
```

#### handle_offer_classified
```python
async def handle_offer_classified(
    self,
    session: AsyncSession,
    title: str,
    category_ids: list[UUID],
    tags: list[str],
    salary_from: int | None,
    salary_to: int | None,
    location: str | None,
) -> None:
    """
    Обработка классифицированной вакансии
    
    - Находит подходящие подписки
    - Отправляет уведомления
    """
```

## Обработчики шины

**Расположение**: `src/modules/job_matcher/handlers.py`

### handle_incoming_telegram_message
```python
@bus.subscribe(BusTopics.TG_MESSAGE_RECEIVED)
async def handle_incoming_telegram_message(message: dict):
    """
    Сохранение вакансии из Telegram
    
    - Получает сообщение из tg.message.received
    - Сохраняет через service.save_job_offer()
    - Отправляет на классификацию
    """
```

### handle_start
```python
@bus.subscribe(BusTopics.BOT_MESSAGE_INCOMING)
async def handle_start(message: dict):
    """
    Обработка команды /start
    
    - Проверяет команду
    - Валидирует обязательный объект user
    - Регистрирует Auth по user.telegram_id
    - Заполняет User и связанный Telegram-профиль
    - Отправляет приветствие
    """
```

### handle_subscribe
```python
@bus.subscribe(BusTopics.BOT_MESSAGE_INCOMING)
async def handle_subscribe(message: dict):
    """
    Обработка команды /subscribe
    
    - Отправляет по 5 активных категорий, номер страницы и навигацию
    - По callback `subscribe_page:<page>` заменяет клавиатуру в том же сообщении
    - По callback `subscribe_category:<category_id>` создаёт или обновляет подписку
    - После выбора заменяет исходное сообщение подтверждением без клавиатуры
    - Повторный выбор категории не создаёт дубликат
    """
```

### handle_job_offer_classified
```python
@bus.subscribe(BusTopics.JOB_OFFER_CLASSIFIED)
async def handle_job_offer_classified(message: dict):
    """
    Обработка классифицированной вакансии
    
    - Обновляет категории вакансии
    - Ищет подходящие подписки
    - Отправляет уведомления через notification.send
    """
```

## События шины

### Подписки (входящие)

#### telegram_clients.event.message.received
```python
# Данные события:
{
  "account_id": "UUID",
  "chat_id": 123456789,
  "message_id": 123,
  "sender": {
    "sender_id": 987654321,
    "username": "vacancy_author",
    "first_name": "Иван",
    "last_name": "Иванов"
  },
  "text": "Вакансия: Python разработчик..."
}
```

**Топик**: `telegram_clients.event.message.received`

**От кого**: `telegram_clients`

**Когда**: При получении нового сообщения из Telegram

#### bot.message.incoming
```python
# Данные события:
{
  "chat_id": 123456789,
  "text": "/start",
  "command": "start",
  "username": "ivanov"
}
```

**Топик**: `bot.message.incoming`

**От кого**: `job_bot`

**Когда**: При получении команды от пользователя

#### text.classify.completed
```python
# Данные события:
{
  "request_id": "UUID",
  "categories": [
    {"slug": "backend", "confidence": 0.95},
    {"slug": "python", "confidence": 0.87}
  ],
  "entities": {
    "salary_from": 100000,
    "salary_to": 200000,
    "employment": "full-time",
    "stack": ["Python", "FastAPI"]
  }
}
```

**Топик**: `text.classify.completed`

**От кого**: `classifier`

**Когда**: После классификации текста

### Публикации (исходящие)

#### text.classify.request
```python
class TextClassifyRequest(BaseEvent):
    """Запрос на классификацию текста"""
    
    request_id: UUID
    text: str
    metadata: dict
```

**Топик**: `text.classify.request`

**Когда публикуется:**
- После сохранения вакансии

**Подписчики:**
- `classifier.handlers` — классификация

#### job.offer.classified
```python
class JobOfferClassified(BaseEvent):
    """Вакансия классифицирована"""
    
    offer_id: UUID
    title: str
    category_ids: list[UUID]
    tags: list[str]
    salary_from: int | None
    salary_to: int | None
    location: str | None
```

**Топик**: `job.offer.classified`

**Когда публикуется:**
- После получения результатов классификации

**Подписчики:**
- `job_matcher.handlers` — поиск подписок

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
- При отправке уведомления о новой вакансии

**Подписчики:**
- `notifications.handlers` — отправка email

## DI-зависимости

**Расположение**: `src/modules/job_matcher/dependencies.py`

```python
def get_job_offer_repository() -> JobOfferRepository:
    """Фабрика репозитория вакансий"""
    return JobOfferRepository()


def get_subscription_repository() -> SubscriptionRepository:
    """Фабрика репозитория подписок"""
    return SubscriptionRepository()


def get_job_offer_service(...) -> JobOfferService: ...
def get_subscription_service(...) -> SubscriptionService: ...
def get_job_matcher_user_service(...) -> JobMatcherUserService: ...

# Варианты без FastAPI Depends для обработчиков шины:
def get_job_offer_service_factory() -> JobOfferService: ...
def get_subscription_service_factory() -> SubscriptionService: ...
def get_job_matcher_user_service_factory() -> JobMatcherUserService: ...
```

## Взаимосвязи с другими модулями

### Зависит от

| Модуль | Тип | Описание |
|--------|-----|----------|
| `bus` | Шина | Публикация/подписка на события |
| `auth` | AuthClient | Регистрация пользователей |
| `users` | UsersClient | Получение данных пользователя |
| `classifier` | Подписка | Классификация вакансий |
| `notifications` | Подписка | Отправка уведомлений |

### Используется

| Модуль | Тип | Описание |
|--------|-----|----------|
| `job_bot` | Подписка | Обработка команд бота |
| `telegram_clients` | Подписка | Получение вакансий из Telegram |

## Клиенты (межмодульное взаимодействие)

### AuthClient

**Расположение**: `src/core/clients/auth_client.py`

```python
class AuthClient:
    """Клиент для взаимодействия с auth модулем"""
    
    async def register_user(
        self,
        session: AsyncSession,
        identifier: str,
        identifier_type: str,
    ) -> UUID:
        """
        Регистрация пользователя
        
        Returns:
            UUID: auth_id нового пользователя
        """
```

### UsersClient

**Расположение**: `src/core/clients/users_client.py`

```python
class UsersClient:
    """Клиент для взаимодействия с users модулем"""
    
    async def get_user_profile(
        self, auth_id: UUID
    ) -> UserRead | None:
        """Получение профиля пользователя"""
    
    async def resolve_email_by_auth_id(
        self, auth_id: UUID
    ) -> str | None:
        """Получение email для отправки уведомлений"""
```

## Алгоритмы

### Поиск подходящих подписок

```python
async def find_matching_subscriptions(
    self,
    session: AsyncSession,
    category_ids: list[UUID],
    tags: list[str],
    salary_from: int | None,
    salary_to: int | None,
    location: str | None,
) -> list[Subscription]:
    """
    Поиск подписок, подходящих под вакансию
    
    Критерии совпадения:
    1. category_ids пересекаются с category_ids подписки
    2. keywords пересекаются с tags вакансии
    3. salary_from >= subscription.min_salary (или min_salary не указан)
    4. salary_to <= subscription.max_salary (или max_salary не указан)
    5. location совпадает с location подписки (или location не указан)
    """
```

### Парсинг вакансий

```python
def parse_job_offer(text: str) -> ParsedJobOffer:
    """
    Парсинг текста вакансии
    
    Извлекает:
    - Заголовок (первая строка)
    - Зарплату (regex: от N до M, N-M, N млн)
    - Локацию (regex: Москва, СПб, remote, удалённо)
    - Теги (хэштеги: #python, #backend)
    - Описание (остальной текст)
    """
```

## Константы

**Расположение**: `src/modules/job_matcher/constants.py`

### ERROR_MESSAGES

```python
ERROR_MESSAGES = {
    "subscription_exists": "Подписка уже существует",
    "subscription_not_found": "Подписка не найдена",
    "offer_not_found": "Вакансия не найдена",
    "user_already_registered": "Пользователь уже зарегистрирован",
}
```

### Шаблоны уведомлений

```python
NOTIFICATION_TEMPLATE = """
🔥 Новая вакансия: {title}

💰 Зарплата: {salary}
📍 Локация: {location}

{description}

#tags: {tags}
"""
```

## Примеры использования

### Сохранение вакансии

```python
async with session.begin():
    offer = await service.save_job_offer(
        session=session,
        text="Python разработчик\nЗарплата: 100000-200000₽\nМосква\n#python #backend",
        chat_id=123456789,
        message_id=123,
    )
    # offer.id содержит UUID вакансии
```

### Создание подписки

```python
async with session.begin():
    subscription = await service.handle_subscribe(
        session=session,
        chat_id=123456789,
        data=SubscriptionCreate(
            keywords=["python", "backend"],
            category_ids=[uuid.UUID("...")],
            min_salary=100000,
            locations=["Москва"],
        ),
    )
```

### Обработка классификации

```python
# В обработчике text.classify.completed
async def handle_job_offer_classified(message: dict):
    offer_id = uuid.UUID(message["offer_id"])
    category_ids = [uuid.UUID(cid) for cid in message["category_ids"]]
    
    await service.update_job_offer_categories(
        session=session,
        job_offer_id=offer_id,
        category_ids=category_ids,
    )
    
    # Поиск подходящих подписок
    matching = await subscription_repository.find_matching(
        session=session,
        category_ids=category_ids,
        tags=message.get("tags", []),
        salary_min=message.get("salary_from"),
        salary_max=message.get("salary_to"),
        location=message.get("location"),
    )
    
    # Отправка уведомлений
    for sub in matching:
        await message_bus.publish(
            BusTopics.NOTIFICATION_SEND,
            NotificationSend(
                auth_id=sub.auth_id,
                template_name="new_job_offer",
                channel="email",
                body={"offer_id": str(offer_id)},
                recipient=None,  # Резолвинг в notifications
            ).to_bus_dict(),
        )
```

## Тестирование

**Расположение тестов**: `tests/modules/job_matcher/`

### Фикстуры

```python
@pytest.fixture
def job_offer_service(offer_repo, sub_repo, message_bus):
    return JobOfferService(offer_repo=offer_repo, sub_repo=sub_repo, bus=message_bus)


@pytest.fixture
def subscription_service(sub_repo, message_bus):
    return SubscriptionService(repository=sub_repo, bus=message_bus)


@pytest.fixture
def offer_repository(db_session):
    return JobOfferRepository()


@pytest.fixture
def subscription_repository(db_session):
    return SubscriptionRepository()
```

### Пример теста

```python
async def test_save_job_offer(db_session, job_matcher_service):
    text = "Python разработчик\nЗарплата: 100000-200000₽\nМосква\n#python #backend"
    
    offer = await job_matcher_service.save_job_offer(
        session=db_session,
        text=text,
        chat_id=123456789,
        message_id=123,
    )
    
    assert offer.title == "Python разработчик"
    assert offer.salary_from == 100000
    assert offer.salary_to == 200000
    assert offer.location == "Москва"
    assert offer.tags == ["python", "backend"]
```

## Миграции Alembic

**Файл миграции**: `alembic/versions/XXXX_create_job_matcher_tables.py`

```python
def upgrade():
    # Вакансии
    op.create_table(
        'job_offers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('salary_from', sa.Integer(), nullable=True),
        sa.Column('salary_to', sa.Integer(), nullable=True),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('source_chat_id', sa.Integer(), nullable=False),
        sa.Column('source_message_id', sa.Integer(), nullable=False),
        sa.Column('telegram_sender_id', sa.BigInteger(), nullable=True),
        sa.Column('telegram_username', sa.String(255), nullable=True),
        sa.Column('telegram_first_name', sa.String(255), nullable=True),
        sa.Column('telegram_last_name', sa.String(255), nullable=True),
        sa.Column('category_ids', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_job_offer_source', 'job_offers', ['source_chat_id', 'source_message_id'], unique=True)
    op.create_index('ix_job_offer_created_at', 'job_offers', ['created_at'])
    
    # Подписки
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('auth_id', sa.UUID(), nullable=False),
        sa.Column('keywords', sa.JSON(), nullable=True),
        sa.Column('category_ids', sa.JSON(), nullable=True),
        sa.Column('min_salary', sa.Integer(), nullable=True),
        sa.Column('max_salary', sa.Integer(), nullable=True),
        sa.Column('locations', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_subscription_auth_id', 'subscriptions', ['auth_id'])
    op.create_index('ix_subscription_is_active', 'subscriptions', ['is_active'])
```

## Дополнительные материалы

- [docs/bus.md](../bus.md) — шина сообщений
- [classifier.md](classifier.md) — модуль классификации
- [notifications.md](notifications.md) — модуль уведомлений
