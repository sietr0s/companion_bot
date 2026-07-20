# Модуль CLASSIFIER

**Расположение**: `src/modules/classifier/`

## Назначение

Классификация текстов вакансий по категориям с использованием zero-shot модели BART. Извлечение сущностей (зарплата, тип занятости, стек) через regex.

## Бизнес-логика

### Основные возможности

- Классификация текстов по категориям (zero-shot learning)
- Извлечение сущностей через regex-паттерны
- Управление категориями (создание, обновление, удаление)
- Инициализация категорий по умолчанию
- Логирование всех классификаций
- Обработка запросов через шину сообщений

## Модели данных

### Category

```python
class Category(BaseModel):
    """Категория для классификации"""
    
    id: UUID                      # Уникальный ID категории
    name: str                     # Название категории
    slug: str                     # Уникальный слаг (идентификатор)
    description: str | None       # Описание категории
    is_active: bool = True        # Статус категории
```

**Индексы:**
- `ix_category_slug` — уникальный индекс на slug
- `ix_category_name` — уникальный индекс на name
- `ix_category_is_active` — для фильтрации активных категорий

### ClassificationLog

```python
class ClassificationLog(BaseModel):
    """Лог классификации текста"""
    
    id: UUID                      # Уникальный ID записи
    text_hash: str                # SHA256 хэш текста (для дедупликации)
    text_preview: str             # Первые 100 символов текста
    category_slug: str            # Слаг категории
    confidence: float             # Уверенность модели (0-1)
    entities: dict                # Извлечённые сущности (JSON)
    request_id: UUID              # ID запроса из шины
    created_at: datetime          # Дата классификации
```

**Индексы:**
- `ix_classification_log_text_hash` — для поиска дубликатов
- `ix_classification_log_request_id` — для связи с запросом

## Репозитории

### CategoryRepository

**Расположение**: `src/modules/classifier/repository.py`

```python
class CategoryRepository(BaseRepository[Category]):
    """Репозиторий для работы с категориями"""
    
    async def get_active_labels(
        self, session: AsyncSession
    ) -> list[str]:
        """
        Получение названий активных категорий
        
        Используется для zero-shot классификации
        """
    
    async def get_by_slug(
        self, session: AsyncSession, slug: str
    ) -> Category | None:
        """Получение категории по слагy"""
    
    async def get_by_name(
        self, session: AsyncSession, name: str
    ) -> Category | None:
        """Получение категории по имени"""
```

### ClassificationLogRepository

```python
class ClassificationLogRepository(BaseRepository[ClassificationLog]):
    """Репозиторий для работы с логами классификации"""
    
    # Методы без дополнительной логики, только CRUD
```

## Сервис

### ClassifierService

**Расположение**: `src/modules/classifier/service.py`

```python
class ClassifierService(BaseService[CategoryRepository, Category]):
    """Бизнес-логика классификации"""
```

### Методы управления категориями

#### create_category
```python
async def create_category(
    self, session: AsyncSession, data: CategoryCreate
) -> Category:
    """
    Создание категории
    
    Raises:
        ConflictError: Если категория с таким slug уже существует
    """
```

#### update_category
```python
async def update_category(
    self,
    session: AsyncSession,
    slug: str,
    data: CategoryUpdate,
) -> Category:
    """
    Обновление категории
    
    Raises:
        NotFoundError: Если категория не найдена
    """
```

#### delete_category
```python
async def delete_category(
    self, session: AsyncSession, slug: str
) -> None:
    """
    Удаление категории
    
    Raises:
        NotFoundError: Если категория не найдена
    """
```

#### get_all_categories
```python
async def get_all_categories(
    self,
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> list[Category]:
    """Получение списка всех категорий с пагинацией"""
```

#### init_default_categories
```python
async def init_default_categories(
    self, session: AsyncSession
) -> None:
    """
    Инициализация категорий по умолчанию
    
    Создаёт 10 стандартных категорий:
    - backend, frontend, fullstack, mobile
    - devops, data_science, design
    - management, qa, analytics
    
    Пропускает существующие категории
    """
```

### Метод классификации

#### process_classify_request
```python
async def process_classify_request(
    self,
    session: AsyncSession,
    request_id: UUID,
    text: str,
) -> TextClassifyCompleted:
    """
    Обработка запроса на классификацию
    
    Процесс:
    1. Получает активные категории из БД
    2. Запускает zero-shot классификатор
    3. Извлекает сущности через NER
    4. Записывает результат в лог
    5. Публикует text.classify.completed
    6. Публикует job.offer.classified (для job_matcher)
    
    Returns:
        TextClassifyCompleted: Результат классификации
    """
```

## AI-компоненты

### CategoryClassifier (Protocol)

**Расположение**: `src/modules/classifier/ai/base.py`

```python
class CategoryClassifier(Protocol):
    """Protocol для классификатора категорий"""
    
    async def classify(
        self, text: str, labels: list[str]
    ) -> ClassifyResult:
        """
        Zero-shot классификация текста
        
        Параметры:
        - text: Текст для классификации
        - labels: Список названий категорий
        
        Returns:
            ClassifyResult: Результаты с confidence scores
        """
```

### EntityExtractor (Protocol)

```python
class EntityExtractor(Protocol):
    """Protocol для извлечения сущностей"""
    
    async def extract(self, text: str) -> EntityResult:
        """
        Извлечение сущностей из текста
        
        Извлекает:
        - Зарплата (from, to, currency)
        - Тип занятости (full-time, part-time, contract)
        - Стек технологий
        
        Returns:
            EntityResult: Извлечённые сущности
        """
```

### ZeroShotCategoryClassifier

**Расположение**: `src/modules/classifier/ai/category.py`

```python
class ZeroShotCategoryClassifier(CategoryClassifier):
    """
    Zero-shot классификатор на основе BART
    
    Модель: facebook/bart-large-mnli
    
    Особенности:
    - Ленивая загрузка модели при первом запросе
    - Кэширование модели в памяти
    - Поддержка candidate_labels динамически
    """
    
    _model: ZeroShotClassificationPipeline | None = None
```

#### Метод classify

```python
async def classify(
    self, text: str, labels: list[str]
) -> ClassifyResult:
    """
    Zero-shot классификация
    
    - Загружает модель при первом вызове
    - Запускает классификацию
    - Возвращает отсортированные результаты
    
    Returns:
        ClassifyResult:
        {
          "categories": [
            {"slug": "backend", "confidence": 0.95},
            {"slug": "python", "confidence": 0.87}
          ]
        }
    """
```

#### get_category_classifier

```python
def get_category_classifier() -> CategoryClassifier:
    """
    Singleton для классификатора
    
    Возвращает один экземпляр на всё приложение
    """
```

### RegexEntityExtractor

**Расположение**: `src/modules/classifier/ai/ner.py`

```python
class RegexEntityExtractor(EntityExtractor):
    """
    Извлечение сущностей через regex-паттерны
    
    Поддерживаемые сущности:
    - Зарплата: "от 100000", "100k-200k", "до 5000$"
    - Тип занятости: "full-time", "part-time", "проектная"
    - Стек: "#python", "django", "postgresql"
    """
```

#### Паттерны

```python
SALARY_PATTERNS = [
    r'от\s*(\d+)\s*(?:тыс\.?|k|K)',  # от 100k
    r'(\d+)\s*-\s*(\d+)\s*(?:тыс\.?|k|K)?',  # 100-200k
    r'до\s*(\d+)\s*(?:тыс\.?|k|K)?',  # до 500k
]

EMPLOYMENT_PATTERNS = [
    r'full[- ]?time',      # Полная занятость
    r'part[- ]?time',      # Частичная занятость
    r'project[- ]?based',  # Проектная работа
    r'удалённо',           # Удалённая работа
    r'офис',               # Офис
]

STACK_PATTERNS = [
    r'#(\w+)',             # #python
    r'\b(python|django|fastapi|postgresql|docker|kubernetes)\b',
]
```

#### Метод extract

```python
async def extract(self, text: str) -> EntityResult:
    """
    Извлечение сущностей
    
    Returns:
        EntityResult:
        {
          "salary_from": 100000,
          "salary_to": 200000,
          "currency": "RUB",
          "employment": "full-time",
          "stack": ["python", "django", "postgresql"]
        }
    """
```

## Обработчики шины

**Расположение**: `src/modules/classifier/handlers.py`

### init_default_categories_on_startup
```python
@bus.subscribe(BusTopics.SYSTEM_STARTUP)
async def init_default_categories_on_startup():
    """
    Инициализация категорий при старте приложения
    
    - Создаёт категории по умолчанию
    - Пропускает существующие
    """
```

### handle_classify_request
```python
@bus.subscribe(BusTopics.TEXT_CLASSIFY_REQUEST)
async def handle_classify_request(message: dict):
    """
    Обработка запроса на классификацию
    
    - Получает text из события
    - Запускает классификатор
    - Извлекает сущности
    - Записывает в лог
    - Публикует text.classify.completed
    - Публикует job.offer.classified
    """
```

## События шины

### Подписки (входящие)

#### text.classify.request
```python
class TextClassifyRequest(BaseEvent):
    """Запрос на классификацию текста"""
    
    request_id: UUID
    text: str
    metadata: dict | None
```

**Топик**: `text.classify.request`

**Когда публикуется:**
- После сохранения вакансии в job_matcher

**От кого:**
- `job_matcher`

**Данные:**
```json
{
  "request_id": "UUID",
  "text": "Python разработчик\nЗарплата: 100000-200000₽\nМосква\n#python #backend",
  "metadata": {
    "offer_id": "UUID",
    "source": "telegram"
  }
}
```

### Публикации (исходящие)

#### text.classify.completed
```python
class TextClassifyCompleted(BaseEvent):
    """Результат классификации"""
    
    request_id: UUID
    categories: list[CategoryScore]
    entities: dict
```

**Топик**: `text.classify.completed`

**Когда публикуется:**
- После завершения классификации

**Подписчики:**
- `job_matcher` — обновление вакансии

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
- После классификации вакансии

**Подписчики:**
- `job_matcher` — поиск подходящих подписок

## HTTP API

### Публичные роуты

**Расположение**: `src/modules/classifier/routers/public.py`

| Метод | Путь | Описание | Auth |
|-------|------|----------|------|
| `POST` | `/classifier/categories` | Создание категории | ✅ Admin |
| `GET` | `/classifier/categories` | Список категорий | ❌ |
| `PATCH` | `/classifier/categories/{slug}` | Обновление категории | ✅ Admin |
| `DELETE` | `/classifier/categories/{slug}` | Удаление категории | ✅ Admin |

#### Примеры запросов

**Создание категории:**
```bash
POST /classifier/categories
Content-Type: application/json
Authorization: Bearer <admin_token>

{
  "name": "Backend Разработка",
  "slug": "backend",
  "description": "Вакансии для backend-разработчиков"
}
```

**Список категорий:**
```bash
GET /classifier/categories?limit=50
```

**Ответ:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Backend Разработка",
    "slug": "backend",
    "description": "Вакансии для backend-разработчиков",
    "is_active": true
  },
  {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "name": "Frontend Разработка",
    "slug": "frontend",
    "description": "Вакансии для frontend-разработчиков",
    "is_active": true
  }
]
```

### Внутренние роуты

**Расположение**: `src/modules/classifier/routers/internal.py`

| Метод | Путь | Описание | Auth |
|-------|------|----------|------|
| `GET` | `/internal/classifier/categories` | Список для внутреннего использования | Service key |

## DI-зависимости

**Расположение**: `src/modules/classifier/dependencies.py`

```python
def get_category_repository() -> CategoryRepository:
    """Фабрика репозитория категорий"""
    return CategoryRepository()


def get_classification_log_repository() -> ClassificationLogRepository:
    """Фабрика репозитория логов"""
    return ClassificationLogRepository()


def get_category_classifier() -> CategoryClassifier:
    """Фабрика классификатора"""
    return ZeroShotCategoryClassifier()


def get_entity_extractor() -> EntityExtractor:
    """Фабрика извлечения сущностей"""
    return RegexEntityExtractor()


def get_classifier_service(
    repo: Annotated[CategoryRepository, Depends(get_category_repository)],
    log_repo: Annotated[ClassificationLogRepository, Depends(get_classification_log_repository)],
    classifier: Annotated[CategoryClassifier, Depends(get_category_classifier)],
    extractor: Annotated[EntityExtractor, Depends(get_entity_extractor)],
) -> ClassifierService:
    """Фабрика сервиса"""
    return ClassifierService(
        repository=repo,
        log_repository=log_repo,
        message_bus=get_producer(),
        classifier=classifier,
        entity_extractor=extractor,
    )


def get_classifier_service_factory() -> ClassifierService:
    """Создать сервис для обработчика шины."""
    return ClassifierService(
        repository=CategoryRepository(),
        log_repository=ClassificationLogRepository(),
        message_bus=get_producer(),
        category_classifier=get_category_classifier(),
        entity_extractor=get_entity_extractor(),
    )
```

## Константы

**Расположение**: `src/modules/classifier/constants.py`

### Категории по умолчанию

```python
DEFAULT_CATEGORIES = [
    {"name": "Backend Разработка", "slug": "backend"},
    {"name": "Frontend Разработка", "slug": "frontend"},
    {"name": "Fullstack Разработка", "slug": "fullstack"},
    {"name": "Mobile Разработка", "slug": "mobile"},
    {"name": "DevOps", "slug": "devops"},
    {"name": "Data Science", "slug": "data_science"},
    {"name": "Design", "slug": "design"},
    {"name": "Management", "slug": "management"},
    {"name": "QA", "slug": "qa"},
    {"name": "Analytics", "slug": "analytics"},
]
```

### ERROR_MESSAGES

```python
ERROR_MESSAGES = {
    "category_exists": "Категория с таким slug уже существует",
    "category_not_found": "Категория не найдена",
    "classification_failed": "Ошибка классификации текста",
    "model_not_loaded": "Модель не загружена",
}
```

### Классификатор

```python
CLASSIFIER_MODEL = "facebook/bart-large-mnli"
CLASSIFIER_DEVICE = -1  # CPU (0 для GPU)
CLASSIFIER_BATCH_SIZE = 4
```

## Взаимосвязи с другими модулями

### Зависит от

| Модуль | Тип | Описание |
|--------|-----|----------|
| `bus` | Шина | Подписка на запросы классификации |
| `transformers` | Библиотека | BART модель для классификации |

### Используется

| Модуль | Тип | Описание |
|--------|-----|----------|
| `job_matcher` | Подписка | Классификация вакансий |

## Производительность

### Оптимизация

1. **Ленивая загрузка модели**
   - Модель загружается при первом запросе
   - Не тратит память при старте

2. **Кэширование**
   - Модель кэшируется в памяти
   - Результаты классификации можно кэшировать по text_hash

3. **Batch обработка**
   - Поддержка пакетной классификации
   - CLASSIFIER_BATCH_SIZE = 4

### Время обработки

- **Загрузка модели**: ~2-3 секунды (при первом запросе)
- **Классификация текста**: ~100-500ms
- **Извлечение сущностей**: ~10-50ms

## Конфигурация

### Переменные окружения

```bash
# CLASSIFIER_MODEL=facebook/bart-large-mnli
CLASSIFIER_MODEL=facebook/bart-large-mnli

# CLASSIFIER_DEVICE=-1  # CPU (0 для GPU)
CLASSIFIER_DEVICE=-1

# CLASSIFIER_BATCH_SIZE=4
CLASSIFIER_BATCH_SIZE=4

# HF_HOME=.cache/huggingface
# В Docker этот каталог подключён к постоянному volume huggingface_cache
HF_HOME=.cache/huggingface
```

При первом обращении модель скачивается из Hugging Face Hub. При следующих
запусках она загружается из дискового кэша. Команда `docker compose down -v`
удаляет именованный volume вместе с кэшем модели.

## Примеры использования

### Классификация текста

```python
# Через шину сообщений
await message_bus.publish(
    BusTopics.TEXT_CLASSIFY_REQUEST,
    TextClassifyRequest(
        request_id=uuid.uuid4(),
        text="Python разработчик\nЗарплата: 100000-200000₽\nМосква\n#python #backend",
        metadata={"offer_id": str(offer_id)},
    ).to_bus_dict(),
)

# Результат придёт в text.classify.completed:
# {
#   "request_id": "UUID",
#   "categories": [
#     {"slug": "backend", "confidence": 0.95},
#     {"slug": "python", "confidence": 0.87}
#   ],
#   "entities": {
#     "salary_from": 100000,
#     "salary_to": 200000,
#     "employment": "full-time",
#     "stack": ["python", "backend"]
#   }
# }
```

### Управление категориями

```python
# Создание категории
async with session.begin():
    category = await service.create_category(
        session=session,
        data=CategoryCreate(
            name="Backend Разработка",
            slug="backend",
            description="Вакансии для backend-разработчиков",
        ),
    )

# Обновление категории
async with session.begin():
    category = await service.update_category(
        session=session,
        slug="backend",
        data=CategoryUpdate(
            description="Обновлённое описание",
        ),
    )

# Удаление категории
async with session.begin():
    await service.delete_category(
        session=session,
        slug="backend",
    )
```

## Тестирование

**Расположение тестов**: `tests/modules/classifier/`

### Фикстуры

```python
@pytest.fixture
def classifier_service(repo, log_repo, message_bus, classifier, extractor):
    return ClassifierService(
        repository=repo,
        log_repository=log_repo,
        message_bus=message_bus,
        classifier=classifier,
        entity_extractor=extractor,
    )


@pytest.fixture
def category_classifier():
    return ZeroShotCategoryClassifier()


@pytest.fixture
def entity_extractor():
    return RegexEntityExtractor()
```

### Пример теста

```python
async def test_classify_text(db_session, classifier_service):
    text = "Python разработчик\nЗарплата: 100000-200000₽\nМосква\n#python #backend"
    
    result = await classifier_service.process_classify_request(
        session=db_session,
        request_id=uuid.uuid4(),
        text=text,
    )
    
    assert len(result.categories) > 0
    assert result.categories[0].confidence > 0.5
    assert result.entities.get("salary_from") == 100000
    assert result.entities.get("salary_to") == 200000
```

## Миграции Alembic

**Файл миграции**: `alembic/versions/XXXX_create_classifier_tables.py`

```python
def upgrade():
    # Категории
    op.create_table(
        'categories',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_category_slug', 'categories', ['slug'], unique=True)
    op.create_index('ix_category_name', 'categories', ['name'], unique=True)
    op.create_index('ix_category_is_active', 'categories', ['is_active'])
    
    # Логи классификации
    op.create_table(
        'classification_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('text_hash', sa.String(), nullable=False),
        sa.Column('text_preview', sa.String(), nullable=False),
        sa.Column('category_slug', sa.String(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('entities', sa.JSON(), nullable=True),
        sa.Column('request_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_classification_log_text_hash', 'classification_logs', ['text_hash'])
    op.create_index('ix_classification_log_request_id', 'classification_logs', ['request_id'])
```

## Дополнительные материалы

- [Hugging Face Transformers](https://huggingface.co/docs/transformers)
- [BART модель](https://huggingface.co/facebook/bart-large-mnli)
- [job_matcher.md](job_matcher.md) — обработка классифицированных вакансий
