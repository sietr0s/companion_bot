# Как добавить новый модуль

Пошаговый гайд по созданию нового бизнес-модуля.

---

## Шаг 1. Создайте структуру директорий

```
src/modules/<module_name>/
├── __init__.py
├── models.py          # SQLAlchemy-модель
├── schemas/
│   ├── __init__.py
│   ├── public/        # Pydantic-схемы публичного HTTP API
│   ├── internal/      # Pydantic-схемы internal API
│   └── events.py      # Pydantic-схемы для событий шины
├── repository.py      # Репозиторий (наследуется от BaseRepository)
├── service.py         # Сервис (наследуется от BaseService)
├── handlers.py        # Обработчики событий шины (опционально)
└── routers/
    ├── __init__.py    # Экспорт public_router/internal_router
    ├── public.py      # /api/v1/public/<module>
    └── internal.py    # /internal/<module>
```

---

## Шаг 2. Определите топики в BusTopics

**До создания событий** — добавьте топики в `src/core/bus_topics.py`:

```python
class BusTopics:
    # ... существующие топики ...

    # Модуль MyModule
    MY_ENTITY_CREATED: str = "my_entity.created"
    MY_ENTITY_UPDATED: str = "my_entity.updated"
    MY_ENTITY_DELETED: str = "my_entity.deleted"
```

---

## Шаг 3. Определите модель (`models.py`)

```python
import uuid
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from src.base.model import BaseModel


class MyEntity(BaseModel):
    __tablename__ = "my_entity"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Ссылка на другой модуль — обычный UUID, без ForeignKey!
    auth_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
```

**Правила:**
- Наследуйтесь от `BaseModel` (даёт `id`, `created_at`, `updated_at`)
- **Никогда** не создавайте ForeignKey на таблицы других модулей
- Ссылки на другие модули — обычные UUID-поля

---

## Шаг 4. Определите API-схемы (`schemas/public/`, `schemas/internal/`)

```python
import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class MyEntityCreate(BaseModel):
    """Поля для создания. auth_id НЕ включаем — он из JWT."""
    name: str = Field(max_length=255)


class MyEntityRead(BaseModel):
    """Полная схема для ответа."""
    id: uuid.UUID
    auth_id: uuid.UUID
    name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MyEntityUpdate(BaseModel):
    """Partial update — все поля опциональны."""
    name: str | None = Field(default=None, max_length=255)
```

**Правила:**
- `Create` — поля для создания (без `id`, без `auth_id` из других модулей)
- `Read` — полная схема с `model_config = {"from_attributes": True}`
- `Update` — все поля опциональны (partial update)
- `auth_id` и другие ID из других модулей — **не в схеме**, передаются как аргументы

---

## Шаг 5. Определите события (`schemas/events.py`)

```python
import uuid
from src.bus.schemes import BaseEvent
from src.core.bus_topics import BusTopics


class MyEntityCreated(BaseEvent):
    event_name: str = BusTopics.MY_ENTITY_CREATED
    entity_id: uuid.UUID
    auth_id: uuid.UUID


class MyEntityUpdated(BaseEvent):
    event_name: str = BusTopics.MY_ENTITY_UPDATED
    entity_id: uuid.UUID
    fields_updated: list[str]


class MyEntityDeleted(BaseEvent):
    event_name: str = BusTopics.MY_ENTITY_DELETED
    entity_id: uuid.UUID
```

**Правила:**
- Наследуйтесь от `BaseEvent` (даёт `timestamp` и метод `to_bus_dict()`)
- `event_name` берите из `BusTopics` — **не хардкодите строки**

---

## Шаг 6. Создайте репозиторий (`repository.py`)

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.base.repository import BaseRepository
from src.modules.my_module.models import MyEntity


class MyEntityRepository(BaseRepository[MyEntity]):
    def __init__(self) -> None:
        super().__init__(MyEntity)

    async def get_by_name(
        self, session: AsyncSession, name: str
    ) -> MyEntity | None:
        stmt = select(MyEntity).where(MyEntity.name == name)
        result = await session.execute(stmt)
        return result.scalars().first()
```

`BaseRepository` уже предоставляет: `get_by_id`, `get_all`, `create`, `update`, `delete`.

---

## Шаг 7. Создайте сервис (`service.py`)

```python
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from src.base.service import BaseService
from src.core.bus_topics import BusTopics
from src.core.exceptions import NotFoundError
from src.modules.my_module.repository import MyEntityRepository
from src.modules.my_module.schemas.public import MyEntityCreate, MyEntityUpdate
from src.modules.my_module.schemas.events import MyEntityCreated


class MyEntityService(BaseService[MyEntityRepository, MyEntity]):
    def __init__(
        self, repository: MyEntityRepository, message_bus: MessageProducer
    ) -> None:
        super().__init__(repository)
        self.message_bus = message_bus

    async def create_entity(
        self, session: AsyncSession, data: MyEntityCreate, auth_id: uuid.UUID
    ) -> None:
        """auth_id пробрасывается из JWT, а не из схемы."""
        values = data.model_dump(exclude_unset=True)
        values["auth_id"] = auth_id
        
        # ✅ Создание через репозиторий
        entity = await self.repository.create(session, values)

        # ✅ Публикация события после успешной операции
        event = MyEntityCreated(entity_id=entity.id, auth_id=auth_id)
        await self.message_bus.publish(
            BusTopics.MY_ENTITY_CREATED, 
            event.to_bus_dict()
        )

    async def get_entity(self, session: AsyncSession, auth_id: uuid.UUID):
        entity = await self.repository.get_by_auth_id(session, auth_id)
        if not entity:
            raise NotFoundError(detail="Сущность не найдена")
        return entity
```

**Правила:**
- `auth_id` и другие ID из других модулей — **передавайте как аргументы**, не из схемы
- Публикуйте события **после** успешной операции
- **НЕ используйте** `session.add()`, `session.commit()`, `session.refresh()` — только методы репозитория!
- Если нужна сложная логика сохранения — создайте метод в репозитории, не в сервисе
- Используйте `BusTopics` для имён топиков

---

## Шаг 8. Создайте обработчики (`handlers.py`)

```python
import logging
from src.bus.interface import MessageConsumer
from src.core.bus_topics import BusTopics

logger = logging.getLogger(__name__)


def register_handlers(consumer: MessageConsumer) -> None:
    @consumer.subscribe(BusTopics.USER_REGISTERED)
    async def handle_user_registered(message: dict) -> None:
        logger.info("Новый пользователь: %s", message.get("auth_id"))

    @consumer.subscribe(BusTopics.PROFILE_UPDATED)
    async def handle_profile_updated(message: dict) -> None:
        logger.info("Профиль обновлён: %s", message.get("auth_id"))
```

**Правила:**
- Подписывайтесь только на топики из `BusTopics`
- Обработчики должны быть **идемпотентными** (безопасными при повторном вызове)
- Не делайте прямых импортов из других модулей

---

## Шаг 9. Создайте роутеры (`routers/public.py`, `routers/internal.py`)

Роутер сам владеет полным префиксом и тегами. `main.py` не должен знать URL модуля.

```python
import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.dependencies import get_current_user, get_db_session
from src.modules.my_module.dependencies import get_my_entity_service
from src.modules.my_module.schemas.public import MyEntityCreate, MyEntityRead
from src.modules.my_module.service import MyEntityService

router = APIRouter(
    prefix="/api/v1/public/my-module",
    tags=["MyModule"],
)


@router.post(
    "/",
    response_model=MyEntityRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_entity(
    data: MyEntityCreate,
    auth_id: uuid.UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: MyEntityService = Depends(get_my_entity_service),
) -> MyEntityRead:
    await service.create_entity(session, data, auth_id)
    return await service.get_entity(session, auth_id)
```

---

## Шаг 10. Создайте файл зависимостей (`dependencies.py`)

Создайте `src/modules/<module_name>/dependencies.py` — **не в `core/dependencies.py`**:

```python
"""
DI-зависимости модуля <module_name>.

Фабрики для внедрения сервиса через FastAPI Depends.
"""

from fastapi import Depends
from src.bus import get_producer
from src.bus.interface import MessageProducer
from src.modules.my_module.repository import MyEntityRepository
from src.modules.my_module.service import MyEntityService


def get_my_entity_repository() -> MyEntityRepository:
    return MyEntityRepository()


def get_my_entity_service(
    repo: MyEntityRepository = Depends(get_my_entity_repository),
) -> MyEntityService:
    return MyEntityService(repository=repo, message_bus=get_producer())
```

**Почему в модуле, а не в `core/dependencies.py`?**
- Модули изолированы — ядро не знает о модулях
- При выносе в микросервис — `dependencies.py` переезжает вместе с модулем
- `src/core/dependencies.py` содержит только **общие** зависимости (БД, JWT)

---

## Шаг 11. Подключите роутер в `main.py`

```python
from src.modules.my_module.routers import public_router, internal_router

app.include_router(public_router)
app.include_router(internal_router)
```

---

## Шаг 12. Зарегистрируйте обработчики в `main.py`

```python
from src.bus import get_consumer
from src.modules.my_module.handlers import register_handlers

register_handlers(get_consumer())
```

---

## Чеклист

- [ ] Структура директорий создана
- [ ] Топики добавлены в `BusTopics`
- [ ] Модель определена (без ForeignKey на другие модули)
- [ ] API-схемы определены (auth_id не в Create-схеме)
- [ ] События определены (event_name из BusTopics)
- [ ] Репозиторий создан (наследуется от BaseRepository)
- [ ] Сервис создан (наследуется от BaseService, принимает MessageProducer)
- [ ] **Сервис НЕ использует** `session.add()`, `session.commit()`, `session.refresh()` — только методы репозитория
- [ ] Обработчики событий созданы (опционально)
- [ ] Роутер создан (auth_id через Depends)
- [ ] Зависимости зарегистрированы в `dependencies.py`
- [ ] Роутер подключён в `main.py`
- [ ] Обработчики зарегистрированы в `main.py`
- [ ] Тесты написаны
