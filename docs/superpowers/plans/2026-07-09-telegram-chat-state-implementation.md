# TelegramChatState Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить модель `TelegramChatState` для хранения ID последнего прочитанного сообщения в чатах Telegram.

**Architecture:** Модель привязана к `TelegramAccount` через ForeignKey с cascade delete. Уникальная пара `(account_id, chat_id)` гарантирует одну запись на чат. Репозиторий предоставляет методы для upsert и поиска, сервис добавляет проверку прав доступа через `auth_id`.

**Tech Stack:** SQLAlchemy 2.0 async, Alembic для миграций, pytest для тестов.

---

### Task 1: Создать модель TelegramChatState

**Files:**
- Modify: `src/modules/telegram_clients/models.py`
- Test: `tests/modules/telegram_clients/test_models.py`

- [ ] **Step 1: Добавить импорт UniqueConstraint в models.py**

В начало файла после импортов:
```python
from sqlalchemy import JSON, BigInteger, Boolean, ForeignKey, String, UniqueConstraint
```

- [ ] **Step 2: Добавить класс модели TelegramChatState**

В конец файла `models.py` после `TelegramSettings`:
```python
class TelegramChatState(BaseModel):
    """
    Состояние чтения чата Telegram-аккаунта.
    
    Хранит ID последнего прочитанного сообщения для каждого чата.
    Уникальная пара (account_id, chat_id) — одна запись на чат.
    """

    __tablename__ = "telegram_chat_state"
    __table_args__ = (
        UniqueConstraint('account_id', 'chat_id'),
    )

    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("telegram_account.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chat_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
    )
    last_read_message_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
```

- [ ] **Step 3: Написать тест на создание модели**

Создать файл `tests/modules/telegram_clients/test_models.py` (или добавить в существующий):
```python
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from src.modules.telegram_clients.models import TelegramAccount, TelegramChatState


@pytest.mark.asyncio
async def test_chat_state_creation(db_session: AsyncSession):
    """Тест создания состояния чтения чата."""
    # Создаём тестовый аккаунт
    auth_id = uuid.uuid4()
    account = TelegramAccount(
        auth_id=auth_id,
        phone="+79991234567",
        session_file="/tmp/test_session",
        is_connected=True,
    )
    db_session.add(account)
    await db_session.commit()
    
    # Создаём состояние чата
    chat_state = TelegramChatState(
        account_id=account.id,
        chat_id=123456789,
        last_read_message_id=100,
    )
    db_session.add(chat_state)
    await db_session.commit()
    
    # Проверяем сохранение
    stmt = select(TelegramChatState).where(TelegramChatState.account_id == account.id)
    result = await db_session.execute(stmt)
    saved_state = result.scalar_one()
    
    assert saved_state.chat_id == 123456789
    assert saved_state.last_read_message_id == 100
    assert saved_state.account_id == account.id


@pytest.mark.asyncio
async def test_chat_state_unique_constraint(db_session: AsyncSession):
    """Тест уникальности пары (account_id, chat_id)."""
    auth_id = uuid.uuid4()
    account = TelegramAccount(
        auth_id=auth_id,
        phone="+79991234567",
        session_file="/tmp/test_session",
        is_connected=True,
    )
    db_session.add(account)
    await db_session.commit()
    
    # Создаём первое состояние
    state1 = TelegramChatState(
        account_id=account.id,
        chat_id=123456789,
        last_read_message_id=100,
    )
    db_session.add(state1)
    await db_session.commit()
    
    # Пытаемся создать дубликат — должна быть ошибка
    state2 = TelegramChatState(
        account_id=account.id,
        chat_id=123456789,
        last_read_message_id=200,
    )
    db_session.add(state2)
    
    with pytest.raises(Exception):  # IntegrityError или аналогичная
        await db_session.commit()
```

- [ ] **Step 4: Запустить тесты**

```bash
pytest tests/modules/telegram_clients/test_models.py -v
```
Ожидаемый результат: PASS

- [ ] **Step 5: Закоммитить**

```bash
git add src/modules/telegram_clients/models.py tests/modules/telegram_clients/test_models.py
git commit -m "feat: добавить модель TelegramChatState"
```

---

### Task 2: Создать репозиторий TelegramChatStateRepository

**Files:**
- Modify: `src/modules/telegram_clients/repository.py`
- Test: `tests/modules/telegram_clients/test_repository.py`

- [ ] **Step 1: Добавить импорт модели**

В начало `repository.py`:
```python
from src.modules.telegram_clients.models import TelegramAccount, TelegramSettings, TelegramChatState
```

- [ ] **Step 2: Создать класс TelegramChatStateRepository**

В конец файла `repository.py`:
```python
class TelegramChatStateRepository(BaseRepository[TelegramChatState]):
    """Репозиторий для работы с состоянием чтения чатов."""

    def __init__(self) -> None:
        super().__init__(TelegramChatState)

    async def get_by_account_and_chat(
        self,
        session: AsyncSession,
        account_id: uuid.UUID,
        chat_id: int,
    ) -> TelegramChatState | None:
        """Получить состояние чтения для конкретного чата."""
        stmt = select(self.model).where(
            self.model.account_id == account_id,
            self.model.chat_id == chat_id,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_last_read(
        self,
        session: AsyncSession,
        account_id: uuid.UUID,
        chat_id: int,
        message_id: int,
    ) -> TelegramChatState:
        """
        Создать или обновить состояние чтения (upsert).
        
        Если запись существует — обновляет last_read_message_id.
        Если нет — создаёт новую.
        """
        existing = await self.get_by_account_and_chat(session, account_id, chat_id)
        
        if existing:
            return await self.update(
                session, existing, {"last_read_message_id": message_id}
            )
        
        return await self.create(
            session,
            {
                "account_id": account_id,
                "chat_id": chat_id,
                "last_read_message_id": message_id,
            },
        )

    async def get_all_by_account(
        self,
        session: AsyncSession,
        account_id: uuid.UUID,
    ) -> list[TelegramChatState]:
        """Получить все состояния чтения для аккаунта."""
        stmt = select(self.model).where(self.model.account_id == account_id)
        result = await session.execute(stmt)
        return list(result.scalars().all())
```

- [ ] **Step 3: Написать тесты на репозиторий**

Добавить в `tests/modules/telegram_clients/test_repository.py`:
```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from src.modules.telegram_clients.models import TelegramAccount, TelegramChatState
from src.modules.telegram_clients.repository import TelegramChatStateRepository


@pytest.fixture
async def test_account(db_session: AsyncSession):
    """Фикстура тестового аккаунта."""
    auth_id = uuid.uuid4()
    account = TelegramAccount(
        auth_id=auth_id,
        phone="+79991234567",
        session_file="/tmp/test_session",
        is_connected=True,
    )
    db_session.add(account)
    await db_session.commit()
    return account


@pytest.mark.asyncio
async def test_get_by_account_and_chat(db_session: AsyncSession, test_account: TelegramAccount):
    """Тест получения состояния по account_id и chat_id."""
    repo = TelegramChatStateRepository()
    
    # Создаём состояние
    state = await repo.create(
        db_session,
        {
            "account_id": test_account.id,
            "chat_id": 123456789,
            "last_read_message_id": 100,
        },
    )
    
    # Получаем
    result = await repo.get_by_account_and_chat(db_session, test_account.id, 123456789)
    
    assert result is not None
    assert result.id == state.id
    assert result.last_read_message_id == 100


@pytest.mark.asyncio
async def test_get_by_account_and_chat_not_found(db_session: AsyncSession, test_account: TelegramAccount):
    """Тест получения несуществующего состояния."""
    repo = TelegramChatStateRepository()
    
    result = await repo.get_by_account_and_chat(db_session, test_account.id, 999999)
    
    assert result is None


@pytest.mark.asyncio
async def test_upsert_last_read_create(db_session: AsyncSession, test_account: TelegramAccount):
    """Тест upsert: создание новой записи."""
    repo = TelegramChatStateRepository()
    
    result = await repo.upsert_last_read(db_session, test_account.id, 123456789, 100)
    
    assert result is not None
    assert result.account_id == test_account.id
    assert result.chat_id == 123456789
    assert result.last_read_message_id == 100


@pytest.mark.asyncio
async def test_upsert_last_read_update(db_session: AsyncSession, test_account: TelegramAccount):
    """Тест upsert: обновление существующей записи."""
    repo = TelegramChatStateRepository()
    
    # Создаём
    await repo.upsert_last_read(db_session, test_account.id, 123456789, 100)
    
    # Обновляем
    result = await repo.upsert_last_read(db_session, test_account.id, 123456789, 200)
    
    assert result is not None
    assert result.last_read_message_id == 200
    
    # Проверяем, что запись одна
    all_states = await repo.get_all_by_account(db_session, test_account.id)
    assert len(all_states) == 1


@pytest.mark.asyncio
async def test_get_all_by_account(db_session: AsyncSession, test_account: TelegramAccount):
    """Тест получения всех состояний аккаунта."""
    repo = TelegramChatStateRepository()
    
    # Создаём несколько состояний
    await repo.upsert_last_read(db_session, test_account.id, 111, 10)
    await repo.upsert_last_read(db_session, test_account.id, 222, 20)
    await repo.upsert_last_read(db_session, test_account.id, 333, 30)
    
    # Получаем все
    all_states = await repo.get_all_by_account(db_session, test_account.id)
    
    assert len(all_states) == 3
    chat_ids = {state.chat_id for state in all_states}
    assert chat_ids == {111, 222, 333}
```

- [ ] **Step 4: Запустить тесты**

```bash
pytest tests/modules/telegram_clients/test_repository.py -v
```
Ожидаемый результат: PASS

- [ ] **Step 5: Закоммитить**

```bash
git add src/modules/telegram_clients/repository.py tests/modules/telegram_clients/test_repository.py
git commit -m "feat: добавить TelegramChatStateRepository"
```

---

### Task 3: Добавить методы в сервис TelegramClientService

**Files:**
- Modify: `src/modules/telegram_clients/service.py`
- Modify: `src/modules/telegram_clients/dependencies.py`
- Test: `tests/modules/telegram_clients/test_service.py`

- [ ] **Step 1: Добавить импорт репозитория**

В начало `service.py`:
```python
from src.modules.telegram_clients.repository import (
    TelegramAccountRepository,
    TelegramSettingsRepository,
    TelegramChatStateRepository,
)
```

- [ ] **Step 2: Обновить конструктор сервиса**

Изменить `__init__` в `TelegramClientService`:
```python
def __init__(
    self,
    repository: TelegramAccountRepository,
    message_bus: MessageBus,
    client_manager: TelegramClientManager,
    settings_repository: TelegramSettingsRepository | None = None,
    chat_state_repository: TelegramChatStateRepository | None = None,
) -> None:
    super().__init__(repository)
    self.message_bus = message_bus
    self.client_manager = client_manager
    self.settings_repository = settings_repository
    self.chat_state_repository = chat_state_repository
```

- [ ] **Step 3: Добавить методы сервиса**

В конец класса `TelegramClientService`:
```python
    # Методы для работы с состоянием чтения чатов

    async def get_chat_state(
        self,
        session: AsyncSession,
        account_id: uuid.UUID,
        auth_id: uuid.UUID,
        chat_id: int,
    ) -> TelegramChatState:
        """Получить состояние чтения чата с проверкой прав доступа."""
        # Проверяем принадлежность аккаунта
        account = await self._get_user_account(session, account_id, auth_id)
        
        if not self.chat_state_repository:
            raise RuntimeError("ChatStateRepository не инициализирован")
        
        state = await self.chat_state_repository.get_by_account_and_chat(
            session, account.id, chat_id
        )
        
        if not state:
            raise NotFoundError(detail="Состояние чтения не найдено")
        
        return state

    async def update_last_read(
        self,
        session: AsyncSession,
        account_id: uuid.UUID,
        auth_id: uuid.UUID,
        chat_id: int,
        message_id: int,
    ) -> TelegramChatState:
        """Обновить ID последнего прочитанного сообщения."""
        # Проверяем принадлежность аккаунта
        account = await self._get_user_account(session, account_id, auth_id)
        
        if not self.chat_state_repository:
            raise RuntimeError("ChatStateRepository не инициализирован")
        
        return await self.chat_state_repository.upsert_last_read(
            session, account.id, chat_id, message_id
        )

    async def get_all_chats_state(
        self,
        session: AsyncSession,
        account_id: uuid.UUID,
        auth_id: uuid.UUID,
    ) -> list[TelegramChatState]:
        """Получить все состояния чтения для аккаунта."""
        # Проверяем принадлежность аккаунта
        account = await self._get_user_account(session, account_id, auth_id)
        
        if not self.chat_state_repository:
            raise RuntimeError("ChatStateRepository не инициализирован")
        
        return await self.chat_state_repository.get_all_by_account(session, account.id)
```

- [ ] **Step 4: Обновить dependencies.py**

Добавить в `src/modules/telegram_clients/dependencies.py`:
```python
from src.modules.telegram_clients.repository import TelegramChatStateRepository

# ... существующий код ...

@inject
def get_chat_state_repository() -> TelegramChatStateRepository:
    """Factory for TelegramChatStateRepository."""
    return TelegramChatStateRepository()
```

- [ ] **Step 5: Написать тесты на сервис**

Добавить в `tests/modules/telegram_clients/test_service.py`:
```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from src.core.exceptions import NotFoundError
from src.modules.telegram_clients.models import TelegramAccount
from src.modules.telegram_clients.repository import TelegramChatStateRepository
from src.modules.telegram_clients.service import TelegramClientService


@pytest.mark.asyncio
async def test_get_chat_state_not_found(db_session: AsyncSession):
    """Тест получения несуществующего состояния."""
    auth_id = uuid.uuid4()
    account = TelegramAccount(
        auth_id=auth_id,
        phone="+79991234567",
        session_file="/tmp/test_session",
        is_connected=True,
    )
    db_session.add(account)
    await db_session.commit()
    
    repo = TelegramAccountRepository()
    chat_state_repo = TelegramChatStateRepository()
    service = TelegramClientService(repo, InMemoryProducer(), TelegramClientManager(), chat_state_repository=chat_state_repo)
    
    with pytest.raises(NotFoundError):
        await service.get_chat_state(db_session, account.id, auth_id, 123456789)


@pytest.mark.asyncio
async def test_update_last_read(db_session: AsyncSession):
    """Тест обновления состояния чтения."""
    auth_id = uuid.uuid4()
    account = TelegramAccount(
        auth_id=auth_id,
        phone="+79991234567",
        session_file="/tmp/test_session",
        is_connected=True,
    )
    db_session.add(account)
    await db_session.commit()
    
    repo = TelegramAccountRepository()
    chat_state_repo = TelegramChatStateRepository()
    service = TelegramClientService(repo, InMemoryProducer(), TelegramClientManager(), chat_state_repository=chat_state_repo)
    
    result = await service.update_last_read(db_session, account.id, auth_id, 123456789, 100)
    
    assert result is not None
    assert result.last_read_message_id == 100
    
    # Обновляем ещё раз
    result2 = await service.update_last_read(db_session, account.id, auth_id, 123456789, 200)
    assert result2.last_read_message_id == 200


@pytest.mark.asyncio
async def test_get_all_chats_state(db_session: AsyncSession):
    """Тест получения всех состояний."""
    auth_id = uuid.uuid4()
    account = TelegramAccount(
        auth_id=auth_id,
        phone="+79991234567",
        session_file="/tmp/test_session",
        is_connected=True,
    )
    db_session.add(account)
    await db_session.commit()
    
    repo = TelegramAccountRepository()
    chat_state_repo = TelegramChatStateRepository()
    service = TelegramClientService(repo, InMemoryProducer(), TelegramClientManager(), chat_state_repository=chat_state_repo)
    
    # Создаём несколько состояний
    await service.update_last_read(db_session, account.id, auth_id, 111, 10)
    await service.update_last_read(db_session, account.id, auth_id, 222, 20)
    await service.update_last_read(db_session, account.id, auth_id, 333, 30)
    
    # Получаем все
    all_states = await service.get_all_chats_state(db_session, account.id, auth_id)
    
    assert len(all_states) == 3
```

- [ ] **Step 6: Запустить тесты**

```bash
pytest tests/modules/telegram_clients/test_service.py -v
```
Ожидаемый результат: PASS

- [ ] **Step 7: Закоммитить**

```bash
git add src/modules/telegram_clients/service.py src/modules/telegram_clients/dependencies.py tests/modules/telegram_clients/test_service.py
git commit -m "feat: добавить методы управления состоянием чтения в сервис"
```

---

### Task 4: Создать миграцию Alembic

**Files:**
- Create: `alembic/versions/<timestamp>_add_telegram_chat_state_table.py`

- [ ] **Step 1: Сгенерировать миграцию**

```bash
alembic revision -m "add_telegram_chat_state_table"
```

- [ ] **Step 2: Заполнить миграцию**

Открыть созданный файл в `alembic/versions/` и добавить:
```python
"""add_telegram_chat_state_table

Revision ID: <auto-generated>
Revises: <previous>
Create Date: 2026-07-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '<auto-generated>'
down_revision: Union[str, None] = '<previous>'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'telegram_chat_state',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('account_id', sa.UUID(), nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('last_read_message_id', sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['telegram_account.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('account_id', 'chat_id'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_telegram_chat_state_account_id', 'telegram_chat_state', ['account_id'], unique=False)
    op.create_index('ix_telegram_chat_state_chat_id', 'telegram_chat_state', ['chat_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_telegram_chat_state_chat_id', table_name='telegram_chat_state')
    op.drop_index('ix_telegram_chat_state_account_id', table_name='telegram_chat_state')
    op.drop_table('telegram_chat_state')
```

- [ ] **Step 3: Применить миграцию**

```bash
alembic upgrade head
```

- [ ] **Step 4: Проверить в БД**

```bash
docker-compose exec app python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, select

engine = create_async_engine('postgresql+asyncpg://user:pass@localhost/dbname')
async with engine.connect() as conn:
    result = await conn.execute(sa.text('SELECT column_name, data_type FROM information_schema.columns WHERE table_name = \\'telegram_chat_state\\''))
    for row in result:
        print(row)
"
```

- [ ] **Step 5: Закоммитить**

```bash
git add alembic/versions/*.py
git commit -m "db: добавить миграцию telegram_chat_state"
```

---

### Task 5: Интеграция в handlers (опционально)

**Files:**
- Modify: `src/modules/telegram_clients/handlers.py`

- [ ] **Step 1: Добавить обработчик обновления состояния**

В `handlers.py` добавить обработчик события `TgMessageReceived`:
```python
@bus.subscribe(BusTopics.TG_MESSAGE_RECEIVED)
async def handle_tg_message_received(message: dict):
    """Обновлять last_read_message_id при получении сообщения."""
    async for session in get_session():
        try:
            chat_state_repo = TelegramChatStateRepository()
            await chat_state_repo.upsert_last_read(
                session,
                uuid.UUID(message["account_id"]),
                message["chat_id"],
                message["message_id"],
            )
            await session.commit()
        except Exception as e:
            logger.exception("Ошибка обновления состояния чтения: %s", e)
            await session.rollback()
            raise
```

- [ ] **Step 2: Запустить тесты**

```bash
pytest tests/modules/telegram_clients/test_handlers.py -v
```

- [ ] **Step 3: Закоммитить**

```bash
git add src/modules/telegram_clients/handlers.py
git commit -m "feat: обновлять состояние чтения при получении сообщений"
```

---

## Checklist

- [ ] Task 1: Модель создана, тесты passing
- [ ] Task 2: Репозиторий создан, тесты passing
- [ ] Task 3: Сервис обновлён, тесты passing
- [ ] Task 4: Миграция создана и применена
- [ ] Task 5: Handlers обновлены (опционально)
