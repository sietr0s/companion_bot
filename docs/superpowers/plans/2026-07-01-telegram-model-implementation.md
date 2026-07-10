# Telegram Model Implementation Plan

> **Для агентов:** REQUIRED SUB-SKILL: Используйте `subagent-driven-development` или `executing-plans` для реализации задачи за задачей.

**Цель:** Добавить отдельную модель `Telegram` с foreign key из `UserProfile` в основном приложении (ms_starter).

**Архитектура:** Создаём новую таблицу `telegram` с данными Telegram-аккаунта, добавляем FK `user_profiles.telegram_id` → `telegram.id`. Модульный подход: модель, репозиторий, сервис, роуты, миграция.

**Технологии:** SQLAlchemy 2.0, Alembic, FastAPI, Pydantic

---

## Структура файлов

**Создать:**
- `src/modules/users/models.py` (обновить, добавить Telegram)
- `src/modules/users/repository.py` (добавить TelegramRepository)
- `src/modules/users/service.py` (добавить методы для Telegram)
- `src/modules/users/internal.py` (добавить роуты для telegram-profiles)
- `src/modules/users/schemas/api.py` (добавить схемы для Telegram)
- `src/modules/users/schemas/events.py` (если нужно)
- `alembic/versions/xxxx_add_telegram_model.py` (миграция)

**Изменить:**
- `src/core/bus_topics.py` (добавить BOT_MESSAGE_SEND)
- `src/modules/notifications/service.py` (опционально, для отправки через бота)

---

## Задачи

### Задача 1: Добавить модель Telegram

**Файлы:**
- Создать: `src/modules/users/models.py` (обновить существующий)

- [ ] **Шаг 1: Добавить класс Telegram**

```python
# src/modules/users/models.py

import uuid
from sqlalchemy import String, Uuid, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.base.model import BaseModel


class Telegram(BaseModel):
    """
    Модель Telegram-аккаунта.

    Хранит данные Telegram: telegram_id, username, имена.
    На неё ссылается UserProfile через foreign key.
    """

    __tablename__ = "telegram"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    telegram_id: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )
    telegram_username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    telegram_first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    telegram_last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Связь с UserProfile (один к одному)
    user_profile: Mapped["UserProfile | None"] = relationship(
        "UserProfile",
        back_populates="telegram",
        uselist=False,
    )
```

- [ ] **Шаг 2: Обновить UserProfile с FK**

```python
# src/modules/users/models.py (добавить после existing fields)

    # Foreign key на Telegram
    telegram_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("telegram.id"),
        nullable=True,
    )

    # Связь с Telegram (один к одному)
    telegram: Mapped[Telegram | None] = relationship(
        "Telegram",
        back_populates="user_profile",
        uselist=False,
    )
```

- [ ] **Шаг 3: Проверить синтаксис**

```bash
python -m py_compile src/modules/users/models.py
```

Ожидаемый результат: OK (без ошибок)

- [ ] **Шаг 4: Коммит**

```bash
git add src/modules/users/models.py
git commit -m "feat: add Telegram model with FK to UserProfile"
```

---

### Задача 2: Добавить репозиторий Telegram

**Файлы:**
- Создать: `src/modules/users/repository.py` (обновить существующий)

- [ ] **Шаг 1: Добавить TelegramRepository**

```python
# src/modules/users/repository.py

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.repository import BaseRepository
from src.modules.users.models import UserProfile, Telegram


class UserRepository(BaseRepository[UserProfile]):
    """Репозиторий профилей пользователей."""

    async def get_by_auth_id(self, session: AsyncSession, auth_id: uuid.UUID):
        """Получить профиль по auth_id."""
        stmt = select(UserProfile).where(UserProfile.auth_id == auth_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


class TelegramRepository(BaseRepository[Telegram]):
    """Репозиторий Telegram-аккаунтов."""

    async def get_by_telegram_id(self, session: AsyncSession, telegram_id: str):
        """Получить Telegram по telegram_id."""
        stmt = select(Telegram).where(Telegram.telegram_id == telegram_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_auth_id(self, session: AsyncSession, auth_id: uuid.UUID):
        """Получить Telegram по auth_id (через UserProfile)."""
        from sqlalchemy.orm import selectinload

        stmt = (
            select(Telegram)
            .join(UserProfile, UserProfile.telegram_id == Telegram.id)
            .where(UserProfile.auth_id == auth_id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_list_with_profiles(
        self,
        session: AsyncSession,
        filters: list | None = None,
        skip: int = 0,
        limit: int = 100,
    ):
        """Получить список Telegram с профилями."""
        stmt = (
            select(Telegram)
            .join(UserProfile, UserProfile.telegram_id == Telegram.id, isouter=True)
            .offset(skip)
            .limit(limit)
        )
        result = await session.execute(stmt)
        return result.scalars().all()
```

- [ ] **Шаг 2: Проверить синтаксис**

```bash
python -m py_compile src/modules/users/repository.py
```

- [ ] **Шаг 3: Коммит**

```bash
git add src/modules/users/repository.py
git commit -m "feat: add TelegramRepository with CRUD methods"
```

---

### Задача 3: Добавить схемы Pydantic

**Файлы:**
- Создать: `src/modules/users/schemas/api.py` (обновить)

- [ ] **Шаг 1: Добавить схемы для Telegram**

```python
# src/modules/users/schemas/api.py

from pydantic import BaseModel, Field
from typing import Optional
import uuid


# --- Telegram Profile ---

class TelegramCreate(BaseModel):
    """Создание Telegram-профиля."""
    auth_id: uuid.UUID
    telegram_id: str = Field(..., min_length=1, max_length=50)
    telegram_username: Optional[str] = Field(None, max_length=100)
    telegram_first_name: Optional[str] = Field(None, max_length=100)
    telegram_last_name: Optional[str] = Field(None, max_length=100)


class TelegramRead(BaseModel):
    """Чтение Telegram-профиля."""
    id: uuid.UUID
    telegram_id: str
    telegram_username: Optional[str]
    telegram_first_name: Optional[str]
    telegram_last_name: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class TelegramUpdate(BaseModel):
    """Обновление Telegram-профиля."""
    telegram_username: Optional[str] = None
    telegram_first_name: Optional[str] = None
    telegram_last_name: Optional[str] = None
```

- [ ] **Шаг 2: Проверить синтаксис**

```bash
python -m py_compile src/modules/users/schemas/api.py
```

- [ ] **Шаг 3: Коммит**

```bash
git add src/modules/users/schemas/api.py
git commit -m "feat: add Pydantic schemas for Telegram"
```

---

### Задача 4: Обновить сервис с методами для Telegram

**Файлы:**
- Создать: `src/modules/users/service.py` (обновить)

- [ ] **Шаг 1: Добавить методы для Telegram в UserService**

```python
# src/modules/users/service.py

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.service import BaseService
from src.bus.interface import MessageBus
from src.core.bus_topics import BusTopics
from src.core.exceptions import NotFoundError
from src.modules.users.models import UserProfile, Telegram
from src.modules.users.repository import UserRepository, TelegramRepository
from src.modules.users.schemas.api import UserCreate, UserUpdate, TelegramCreate


class UserService(BaseService[UserRepository]):
    """Сервис управления профилями пользователей."""

    def __init__(
        self,
        repository: UserRepository,
        telegram_repository: TelegramRepository,
        message_bus: MessageBus,
    ) -> None:
        super().__init__(repository)
        self.telegram_repository = telegram_repository
        self.message_bus = message_bus

    # ... существующие методы ...

    async def create_telegram_profile(
        self,
        session: AsyncSession,
        auth_id: uuid.UUID,
        telegram_id: str,
        telegram_username: str | None = None,
        telegram_first_name: str | None = None,
        telegram_last_name: str | None = None,
    ) -> Telegram:
        """Создать Telegram-профиль и связать с UserProfile."""
        # 1. Проверить, есть ли уже Telegram
        existing = await self.telegram_repository.get_by_telegram_id(session, telegram_id)
        if existing:
            raise ConflictError(detail="Telegram-аккаунт уже привязан")

        # 2. Создать Telegram
        telegram = await self.telegram_repository.create(session, {
            "telegram_id": telegram_id,
            "telegram_username": telegram_username,
            "telegram_first_name": telegram_first_name,
            "telegram_last_name": telegram_last_name,
        })

        # 3. Найти UserProfile
        profile = await self.repository.get_by_auth_id(session, auth_id)
        if not profile:
            raise NotFoundError(detail="Профиль пользователя не найден")

        # 4. Связать через foreign key
        profile.telegram_id = telegram.id
        await session.commit()
        await session.refresh(profile)

        return telegram

    async def get_profile_with_telegram(
        self,
        session: AsyncSession,
        auth_id: uuid.UUID,
    ) -> UserProfile | None:
        """Получить профиль с подгруженным Telegram."""
        from sqlalchemy.orm import selectinload

        stmt = (
            select(UserProfile)
            .options(selectinload(UserProfile.telegram))
            .where(UserProfile.auth_id == auth_id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
```

- [ ] **Шаг 2: Проверить синтаксис**

```bash
python -m py_compile src/modules/users/service.py
```

- [ ] **Шаг 3: Коммит**

```bash
git add src/modules/users/service.py
git commit -m "feat: add Telegram methods to UserService"
```

---

### Задача 5: Создать миграцию Alembic

**Файлы:**
- Создать: `alembic/versions/xxxx_add_telegram_model.py`

- [ ] **Шаг 1: Сгенерировать миграцию**

```bash
cd /home/work/23066359@sigma.sbrf.ru/IdeaProjects/ms_starter
alembic revision --autogenerate -m "add telegram model with fk to user_profiles"
```

- [ ] **Шаг 2: Проверить сгенерированную миграцию**

Открыть файл в `alembic/versions/xxxx_*.py` и убедиться, что есть:
- `op.create_table("telegram", ...)`
- `op.add_column("user_profiles", ...telegram_id...)`
- `op.create_foreign_key(...)`

- [ ] **Шаг 3: Применить миграцию**

```bash
alembic upgrade head
```

- [ ] **Шаг 4: Проверить БД**

```bash
psql -U postgres -d modular_monolith -c "\dt"
psql -U postgres -d modular_monolith -c "SELECT * FROM telegram LIMIT 1;"
```

- [ ] **Шаг 5: Коммит миграции**

```bash
git add alembic/versions/xxxx_add_telegram_model.py
git commit -m "feat: add Alembic migration for Telegram model"
```

---

### Задача 6: Добавить топик в BusTopics

**Файлы:**
- Создать: `src/core/bus_topics.py` (обновить)

- [ ] **Шаг 1: Добавить BOT_MESSAGE_SEND**

```python
# src/core/bus_topics.py

class BusTopics(StrEnum):
    # ... существующие топики ...
    BOT_MESSAGE_SEND = "bot.message.send"  # Отправить сообщение через бота
```

- [ ] **Шаг 2: Проверить синтаксис**

```bash
python -m py_compile src/core/bus_topics.py
```

- [ ] **Шаг 3: Коммит**

```bash
git add src/core/bus_topics.py
git commit -m "feat: add BOT_MESSAGE_SEND topic to BusTopics"
```

---

### Задача 7: Тесты

**Файлы:**
- Создать: `tests/modules/users/test_telegram.py`

- [ ] **Шаг 1: Написать тест для создания Telegram**

```python
# tests/modules/users/test_telegram.py

import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.users.models import Telegram, UserProfile
from src.modules.users.repository import TelegramRepository, UserRepository
from src.modules.users.service import UserService
from src.bus.in_memory.producer import InMemoryProducer


@pytest.mark.asyncio
async def test_create_telegram_profile(db_session: AsyncSession):
    """Тест создания Telegram-профиля."""
    # 1. Создать UserProfile
    user_repo = UserRepository()
    profile = await user_repo.create(db_session, {
        "auth_id": uuid.uuid4(),
        "first_name": "Ivan",
    })

    # 2. Создать Telegram
    telegram_repo = TelegramRepository()
    service = UserService(user_repo, telegram_repo, InMemoryProducer())

    telegram = await service.create_telegram_profile(
        session=db_session,
        auth_id=profile.auth_id,
        telegram_id="123456789",
        telegram_username="@ivan",
        telegram_first_name="Ivan",
    )

    # 3. Проверить
    assert telegram.telegram_id == "123456789"
    assert telegram.telegram_username == "@ivan"
    assert telegram.user_profile_id == profile.id
```

- [ ] **Шаг 2: Запустить тест**

```bash
pytest tests/modules/users/test_telegram.py -v
```

- [ ] **Шаг 3: Коммит тестов**

```bash
git add tests/modules/users/test_telegram.py
git commit -m "test: add tests for Telegram model"
```

---

## Итоговый чек-лист

- [ ] Модель `Telegram` создана
- [ ] Foreign key `user_profiles.telegram_id` → `telegram.id` добавлен
- [ ] Репозиторий `TelegramRepository` с CRUD методами
- [ ] Сервис `UserService` с методами для Telegram
- [ ] Миграция Alembic применена
- [ ] Топик `BOT_MESSAGE_SEND` добавлен
- [ ] Тесты написаны и проходят
- [ ] Код проверен линтером (`ruff check src/`)

---

**Следующий шаг:** После реализации — перейти к созданию бот-сервиса.
