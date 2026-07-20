# Styleguide проекта ms_starter

Документ описывает стиль кода, паттерны и соглашения, принятые в проекте ms_starter (Modular Monolith Starter).

---

## Содержание

1. [Обработчики ошибок](#1-обработчики-ошибок)
2. [Логирование](#2-логирование)
3. [Типизация](#3-типизация)
4. [Именование](#4-именование)
5. [Структура файлов](#5-структура-файлов)
6. [Работа с БД](#6-работа-с-бд)
7. [HTTP обработчики (FastAPI)](#7-http-обработчики-fastapi)
8. [Асинхронность](#8-асинхронность)
9. [Межмодульное взаимодействие](#9-межмодульное-взаимодействие)

---

## ⚡ Краткая памятка

**Сервисы — НЕ работают с сессией напрямую:**
- ❌ `session.add()` → ✅ `repository.create()`
- ❌ `session.commit()` → ✅ внутри `repository.create()/update()`
- ❌ `session.refresh()` → ✅ внутри `repository.create()/update()`
- ❌ `session.execute(select(Model))` → ✅ `repository.get_by_id()`

---

## 1. Обработчики ошибок

### 1.1. Иерархия исключений

В проекте используется централизованная иерархия исключений в `src/core/exceptions.py`:

**Правильно:**
```python
class AppException(Exception):
    """Базовое исключение приложения с HTTP-статусом."""
    def __init__(self, status_code: int = 500, detail: str = "Внутренняя ошибка сервера"):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)

class NotFoundError(AppException):
    """Ресурс не найден (404)."""
    def __init__(self, detail: str = "Ресурс не найден"):
        super().__init__(status_code=404, detail=detail)

class ConflictError(AppException):
    """Конфликт — дублирование уникального поля (409)."""
    def __init__(self, detail: str = "Конфликт данных"):
        super().__init__(status_code=409, detail=detail)

class UnauthorizedError(AppException):
    """Ошибка авторизации (401)."""
    def __init__(self, detail: str = "Не авторизован"):
        super().__init__(status_code=401, detail=detail)
```

### 1.2. Использование в сервисах

Сервисы **должны** выбрасывать исключения, а не возвращать `None` или обрабатывать ошибки локально:

**Правильно:**
```python
# src/modules/users/service.py
async def get_profile(self, session: AsyncSession, auth_id: UUID):
    profile = await self.repository.get_by_auth_id(session, auth_id)
    if not profile:
        raise NotFoundError(detail=ERROR_MESSAGES["profile_not_found"])
    return profile
```

**Неправильно:**
```python
# ❌ Не возвращать None при ошибке
async def get_profile(self, session, auth_id):
    profile = await self.repository.get_by_auth_id(session, auth_id)
    if not profile:
        return None  # ❌ Вызывающий должен проверить None
    return profile

# ❌ Не обрабатывать ошибки локально
async def get_profile(self, session, auth_id):
    try:
        profile = await self.repository.get_by_auth_id(session, auth_id)
        if not profile:
            raise NotFoundError(detail="Not found")
        return profile
    except Exception:
        logger.exception("Ошибка")
        return None
```

### 1.3. Глобальный обработчик в FastAPI

Все исключения `AppException` обрабатываются одним глобальным handler'ом в `main.py`:

```python
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )
```

**Правило:** Не создавайте локальные try/except в роутерах и обработчиках шины — пусть исключения пробрасываются наверх.

---

## 2. Логирование

### 2.1. Стандартный подход

Используйте модуль `logging` с `%`-форматированием:

**Правильно:**
```python
import logging

logger = logging.getLogger(__name__)

logger.info("Пользователь создан: auth_id=%s", auth_id)
logger.warning("Email не найден для auth_id=%s", auth_id)
logger.error("Ошибка загрузки файла: %s", filename)
logger.exception("Критическая ошибка при обработке")  # С трассировкой
```

**Неправильно:**
```python
# ❌ f-строки в логгере (создаются даже при отключенном логировании)
logger.info(f"Пользователь создан: auth_id={auth_id}")

# ❌ print вместо logger
print("Ошибка!")

# ❌ logger.error без трассировки в except
try:
    ...
except Exception:
    logger.error("Произошла ошибка")  # ❌ Нет трассировки
```

### 2.2. Уровни логирования

- `debug` — детальная информация для отладки
- `info` — нормальные события (создание, обновление, удаление)
- `warning` — предупреждения (не критично, но值得关注)
- `error` — ошибки, которые обработаны и не влияют на работу
- `exception` — ошибки с трассировкой стека (в блоках `except`)

---

## 3. Типизация

### 3.1. Полный синтаксис аннотаций

Проект использует полную типизацию с Python 3.10+ синтаксисом:

**Правильно:**
```python
from collections.abc import AsyncGenerator
from typing import Protocol
import uuid

class UserService:
    async def get_profile(self, session: AsyncSession, auth_id: UUID) -> User:
        ...

    async def get_users(
        self,
        session: AsyncSession,
        filters: list[Filter] | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[User]:
        ...

    async def resolve_email(
        self,
        session: AsyncSession,
        auth_id: UUID,
    ) -> str | None:
        ...
```

**Неправильно:**
```python
# ❌ Any вместо конкретных типов
async def get_profile(self, session, auth_id) -> Any:
    ...

# ❌ Старый синтаксис Optional
from typing import Optional, List
async def get_users(self, session, filters: Optional[List[Filter]] = None) -> List[User]:
    ...
```

### 3.2. Protocol для интерфейсов

Используйте `Protocol` для структурной типизации:

**Правильно:**
```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class UserServiceProtocol(Protocol):
    async def get_profile(self, session: AsyncSession, auth_id: UUID) -> User:
        ...

    async def resolve_email_by_auth_id(
        self, session: AsyncSession, auth_id: UUID
    ) -> str | None:
        ...
```

---

## 4. Именование

### 4.1. Соглашения

| Элемент | Стиль | Пример |
|---------|-------|--------|
| Переменные, функции | `snake_case` | `auth_id`, `get_profile()` |
| Классы | `PascalCase` | `UserService`, `TelegramClientManager` |
| Константы | `UPPER_SNAKE_CASE` | `ERROR_MESSAGES`, `MAX_RETRY_COUNT` |
| Топики шины | `dot.notation` | `user.registered`, `tg.message.send` |
| Файлы модулей | `snake_case` | `users_client.py`, `handlers.py` |
| Файлы конфигурации | `kebab-case` или `snake_case` | `pyproject.toml`, `docker-compose.yml` |

### 4.2. Имена переменных

**Правильно:**
```python
auth_id: UUID  # Не user_id (т.к. это auth_id из JWT)
file_id: UUID  # Не file_uuid (UUID — тип, не имя)
storage_key: str  # Не key (контекст ясен из имени переменной)
media_list: list[dict]  # Не media (ясно, что список)
```

**Неправильно:**
```python
# ❌ Сокращения без смысла
uid: UUID  # Что это? user_id? auth_id?
f_id: UUID  # file_id? folder_id?
lst: list  # Что в списке?
```

### 4.3. Имена функций

**Правильно:**
```python
# Глаголы для действий
create_profile(), update_profile(), delete_profile()
resolve_email_by_auth_id()  # Ясно что и как резолвится
upload_media_to_storage()   # Полное описание действия

# get_ для получения с сессией
get_profile(session, auth_id)  # Требуется session
```

---

## 5. Структура файлов

### 5.1. Модульная архитектура

```
src/
├── base/                 # Базовые абстракции (репозиторий, сервис, модель)
├── core/                 # Ядро (config, database, security, clients, dependencies)
├── bus/                  # Шина сообщений (interface, in_memory, kafka)
└── modules/              # Бизнес-модули
    ├── auth/
    ├── users/
    ├── telegram_clients/
    ├── notifications/
    └── media/
```

### 5.2. Структура модуля

```
modules/users/
├── models.py            # SQLAlchemy модели
├── repository.py        # Репозиторий (CRUD + кастомные запросы)
├── service.py           # Бизнес-логика (использует репозиторий)
├── schemas/
│   ├── public/         # Pydantic-схемы публичного API
│   ├── internal/       # Pydantic-схемы internal API
│   └── events.py       # Схемы событий шины
├── routers/
│   ├── public.py       # Владеет /api/v1/public/<module>
│   └── internal.py     # Владеет /internal/<module>
└── handlers.py         # Обработчики событий шины
```

**Правило:** Модули не импортируют друг друга напрямую — только через шину или клиенты.

---

## 6. Работа с БД

### 6.1. Модели SQLAlchemy 2.0

**Правильно:**
```python
from sqlalchemy import String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from src.base.model import BaseModel

class User(BaseModel):
    __tablename__ = "user"

    auth_id: Mapped[UUID] = mapped_column(Uuid, unique=True, index=True)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
```

### 6.2. Репозитории

**Правильно:**
```python
from src.base.repository import BaseRepository
from src.modules.users.models import User

class UserRepository(BaseRepository[User]):
    """Репозиторий профилей пользователей."""

    async def get_by_auth_id(self, session: AsyncSession, auth_id: UUID):
        stmt = select(User).where(User.auth_id == auth_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
```

### 6.3. Сессии и транзакции

**Правильно (в роутерах):**
```python
from src.core.database import get_session

@app.post("/users/")
async def create_user(
    data: UserCreate,
    session: AsyncSession = Depends(get_session),
    service: UserService = Depends(get_user_service),
):
    await service.create_user_profile(session, auth_id, data)
    await session.commit()
```

**Правильно (в клиентах):**
```python
# Клиенты сами управляют сессией
async def resolve_email_by_auth_id(self, auth_id: UUID) -> str | None:
    async for session in get_session():
        profile = await self._service.get_profile(session, auth_id)
        return getattr(profile, "email", None) if profile else None
```

**Неправильно:**
```python
# ❌ Не создавать сессию вручную
session = AsyncSession(engine)
try:
    ...
```

---

### 6.4. Работа сервисов с БД

**Важное правило:** Сервисы **НЕ должны** напрямую работать с сессией БД. Все операции с БД делегируются репозиторию.

**Правильно:**
```python
# ✅ Сервис использует только методы репозитория
class UserService(BaseService[UserRepository, User]):
    async def create_profile(self, session: AsyncSession, auth_id: UUID, data: dict):
        # Создание через репозиторий
        profile = await self.repository.create(session, {
            "auth_id": auth_id,
            **data
        })
        
        # Обновление через репозиторий
        await self.repository.update(session, profile, {"first_name": "Имя"})
        
        # Получение через репозиторий
        existing = await self.repository.get_by_id(session, profile_id)
        
        return profile
```

**Неправильно:**
```python
# ❌ Сервис напрямую работает с сессией
class UserService(BaseService[UserRepository, User]):
    async def create_profile(self, session: AsyncSession, auth_id: UUID, data: dict):
        # Прямое создание модели ❌
        profile = User(auth_id=auth_id, **data)
        session.add(profile)      # ❌ Прямой вызов session.add()
        await session.commit()    # ❌ Прямой вызов session.commit()
        await session.refresh(profile)  # ❌ Прямой вызов session.refresh()
        return profile
```

**Почему это важно:**

| Аспект | Сервис через репозиторий ✅ | Сервис напрямую с сессией ❌ |
|--------|---------------------------|----------------------------|
| **Разделение ответственности** | Сервис — бизнес-логика, репозиторий — БД | Смешение логики и персистентности |
| **Тестируемость** | Легко замокать репозиторий | Требуется мокать сессию SQLAlchemy |
| **Миграция на микросервисы** | Замена репозитория на HTTP-клиент | Требуется переписывание сервиса |
| **Согласованность** | Все CRUD через базовые методы | Разные подходы в разных сервисах |

**Базовые методы репозитория (из `BaseRepository`):**

```python
# CRUD операции
await self.repository.create(session, data_dict)           # Создание
await self.repository.get_by_id(session, id)              # Получение по ID
await self.repository.update(session, obj, data_dict)     # Обновление
await self.repository.delete(session, obj)                # Удаление
await self.repository.get_all(session, skip, limit)       # Список с пагинацией
await self.repository.get_list(session, filters, ...)     # Список с фильтрами
await self.repository.count(session, filters)             # Подсчёт записей
```

**Если нужна сложная логика сохранения:**

```python
# ✅ Создайте кастомный метод в репозитории
class JobOfferRepository(BaseRepository[JobOffer]):
    async def create_from_telegram(
        self,
        session: AsyncSession,
        text: str,
        chat_id: int,
    ) -> JobOffer:
        """Создать вакансию из Telegram-сообщения."""
        return await self.create(session, {
            "title": text[:500],
            "description": text,
            "source_chat_id": chat_id,
            "source_message_id": 0,
        })

# ✅ Используйте в сервисе
class JobOfferService(BaseService[JobOfferRepository, JobOffer]):
    async def save_job_offer(self, session: AsyncSession, text: str, chat_id: int):
        return await self.repository.create_from_telegram(session, text, chat_id)
```

**Чек-лист для сервиса:**

- [ ] Нет `session.add()` — используется `repository.create()`
- [ ] Нет `session.commit()` — commit внутри `repository.create()/update()`
- [ ] Нет `session.refresh()` — refresh внутри `repository.create()/update()`
- [ ] Нет прямых SQL-запросов (`select(Model)`) — используется `repository.get_by_id()` и другие методы
- [ ] Нет `session.execute()` — используется `repository.get_list()` или кастомные методы репозитория
finally:
    await session.close()
```

---

## 7. HTTP обработчики (FastAPI)

### 7.1. Роуты

**Правильно:**
```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_session
from src.core.dependencies import get_user_service
from src.modules.users.service import UserService

router = APIRouter()

@router.post("/")
async def create_user(
    data: UserCreate,
    session: AsyncSession = Depends(get_session),
    service: UserService = Depends(get_user_service),
):
    auth_id = await get_current_user()  # Из JWT
    await service.create_user_profile(session, auth_id, data)
    await session.commit()
    return {"status": "created"}
```

**Неправильно:**
```python
# ❌ Не обрабатывать ошибки локально
@router.post("/")
async def create_user(session: AsyncSession = Depends(get_session)):
    try:
        await service.create_user_profile(session, auth_id, data)
        await session.commit()
        return {"status": "created"}
    except NotFoundError as e:
        return JSONResponse(status_code=404, content={"detail": e.detail})  # ❌
    except Exception:
        logger.exception("Ошибка")
        return JSONResponse(status_code=500, content={"detail": "Error"})  # ❌
```

### 7.2. Зависимости (DI)

**Правильно:**
```python
# src/modules/users/dependencies.py
def get_user_service(
    repo: UserRepository = Depends(get_user_repository),
    producer: MessageProducer = Depends(get_producer),
) -> UserService:
    return UserService(repository=repo, message_bus=producer)
```

**Неправильно:**
```python
# ❌ Не импортировать сервисы напрямую
from src.modules.users.service import UserService

@router.post("/")
async def create_user():
    service = UserService(...)  # ❌ Нет DI
```

---

## 8. Асинхронность

### 8.1. async/await

**Правильно:**
```python
# Все I/O операции должны быть async
async def get_profile(self, session: AsyncSession, auth_id: UUID):
    return await self.repository.get_by_auth_id(session, auth_id)

# async for для итерации
async for session in get_session():
    data = await service.get_data(session)
    yield data

# async with для контекстных менеджеров
async with httpx.AsyncClient() as client:
    response = await client.get(url)
```

**Неправильно:**
```python
# ❌ Синхронные функции для I/O
def get_profile(self, session, auth_id):  # ❌ Нет async
    return self.repository.get_by_auth_id(session, auth_id)

# ❌ Забыть await
async def process():
    result = service.get_data(session)  # ❌ Должно быть await
```

### 8.2. Fire-and-forget

Для задач, не требующих ожидания результата:

**Правильно:**
```python
from asyncio import create_task

@router.post("/upload")
async def upload_file():
    result = await service.upload()
    # Асинхронно отправить уведомление без ожидания
    create_task(notify_user(result.user_id))
    return result
```

---

## 9. Межмодульное взаимодействие

### 9.1. Клиенты для прямого вызова (текущая реализация)

**Важно:** В текущей реализации (Modular Monolith) клиенты используют **прямые импорты сервисов** модулей. Это осознанное решение для монолитной архитектуры.

**Правильно:**
```python
# src/modules/notifications/service.py
from src.core.clients import UsersClient

class NotificationService:
    async def send_notification(self, session, auth_id: UUID):
        client = UsersClient()
        email = await client.resolve_email_by_auth_id(auth_id)
        # Отправить уведомление на email
```

**Почему импорты, а не HTTP:**

| Критерий | Импорты (сейчас) | HTTP (в будущем) |
|----------|------------------|------------------|
| Архитектура | Modular Monolith | Микросервисы |
| Производительность | Прямые вызовы | Сетевые запросы |
| Типизация | Полная | Через OpenAPI схемы |
| Тестирование | Легко мокать | Требуется HTTP mock |
| Масштабирование | Общее | Независимое |

**План миграции:**

При выносе модулей в микросервисы клиенты будут переписаны на HTTP:

```python
# Будущая реализация (микросервисы):
class UsersClient:
    async def resolve_email_by_auth_id(self, auth_id: UUID) -> str | None:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.USERS_SERVICE_URL}/internal/users/",
                params={"filters": f"auth_id+eq+{auth_id}"}
            )
            data = response.json()
            return data[0].get("email") if data else None
```

**Неправильно:**
```python
# ❌ Не делать HTTP-запросы вручную (пока не migrated на микросервисы)
async def send_notification(self, session, auth_id):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://localhost:8000/internal/users/?filters=auth_id+eq+{auth_id}")
        # ❌ Использовать клиенты вместо прямых запросов
```

### 9.2. Шина сообщений

Для асинхронного взаимодействия:

**Правильно (публикация):**
```python
# src/modules/auth/service.py
class AuthService:
    async def register(self, session, data: RegisterRequest):
        account = await self.repository.create(session, data)
        await self.message_bus.publish(
            BusTopics.USER_REGISTERED,
            UserRegistered(auth_id=account.id, email=data.email).to_bus_dict(),
        )
```

**Правильно (подписка):**
```python
# src/modules/users/handlers.py
def register_handlers(consumer: MessageConsumer):
    @consumer.subscribe(BusTopics.USER_REGISTERED)
    async def handle_user_registered(message: dict):
        logger.info("Новый пользователь: auth_id=%s", message.get("auth_id"))
        # Создать профиль пользователя
```

**Неправильно:**
```python
# ❌ Не импортировать сервисы других модулей
from src.modules.auth.service import AuthService  # ❌

# ❌ Не вызывать методы других модулей напрямую
await auth_service.register(...)  # ❌
```

---

## 10. Чек-лист перед коммитом

Перед тем как закоммитить код, проверьте:

- [ ] Все функции имеют type hints
- [ ] Нет `try/except` в обработчиках шины (кроме логирования)
- [ ] Исключения пробрасываются из сервисов (не возвращаем `None`)
- [ ] Используется `%`-форматирование в логгере
- [ ] Нет прямых импортов между модулями
- [ ] Все I/O операции асинхронные (`async/await`)
- [ ] Сессии БД управляются через `Depends(get_session)`
- [ ] Имена переменных описательные (`auth_id`, не `uid`)
- [ ] Нет `print()` в коде (только `logger`)
- [ ] Клиенты используют DI для получения session

---

## 11. Примеры из реального кода

### 11.1. Сервис с правильными исключениями

```python
# src/modules/users/service.py
class UserService(BaseService[UserRepository, User]):
    async def get_profile(self, session: AsyncSession, auth_id: UUID):
        """Получить профиль по auth_id. Raise NotFoundError если не найден."""
        profile = await self.repository.get_by_auth_id(session, auth_id)
        if not profile:
            raise NotFoundError(detail=ERROR_MESSAGES["profile_not_found"])
        return profile
```

### 11.2. Обработчик шины без try/except

```python
# src/modules/telegram_clients/handlers.py
@bus.subscribe(BusTopics.TG_MESSAGE_SEND)
async def handle_send_message(message: dict) -> None:
    account_id_str = message.get("account_id")
    chat_id = message.get("chat_id")
    text = message.get("text", "")

    if not account_id_str or not chat_id or not text:
        logger.warning("Неполные данные для отправки: %s", message)
        return

    account_id = uuid.UUID(account_id_str)
    await client_manager.send_message(account_id, int(chat_id), text)
    logger.info("Сообщение отправлено: account=%s, chat=%s", account_id, chat_id)
```

### 11.3. Клиент с DI

```python
# src/core/clients/users_client.py
class UsersClient:
    async def resolve_email_by_auth_id(self, auth_id: UUID) -> str | None:
        try:
            service = get_user_service()
            async for session in get_session():
                profile = await service.get_profile(session, auth_id)
                return getattr(profile, "email", None) if profile else None
        except Exception:
            logger.exception("Ошибка при резолве email для auth_id: %s", auth_id)
            return None
```

---

## 12. DI-зависимости

### 12.1. Где регистрировать зависимости

Зависимости регистрируются **в модулях**, а не в `core/dependencies.py`:

```
src/modules/<module_name>/dependencies.py  ✅ — в модуле
src/core/dependencies.py                   ❌ — только общие
```

**Правильно:** `src/modules/auth/dependencies.py`
```python
from fastapi import Depends
from src.bus import get_producer
from src.bus.interface import MessageProducer
from src.modules.auth.repository import AuthRepository
from src.modules.auth.service import AuthService


def get_auth_repository() -> AuthRepository:
    return AuthRepository()


def get_auth_service(
    repo: AuthRepository = Depends(get_auth_repository),
    bus: MessageProducer = Depends(get_producer),
) -> AuthService:
    return AuthService(repository=repo, message_bus=bus)
```

**Неправильно:** `src/core/dependencies.py`
```python
from src.modules.auth.service import AuthService  # ❌ — ядро знает о модуле
```

### 12.2. Что остаётся в `core/dependencies.py`

Только **общие** зависимости:
- `get_db_session()` — сессия БД
- `get_current_user()` / `get_current_admin()` — JWT-авторизация
- `get_users_client()` / `get_media_client()` — клиенты для межмодульного взаимодействия

### 12.3. Почему так?

- **Изоляция** — при выносе модуля в микросервис, `dependencies.py` переезжает вместе с ним
- **Нет циклических зависимостей** — модули не импортируют `core`, `core` не импортирует модули
- **Тестируемость** — можно замокать модульные зависимости, не трогая ядро

---

## 12. Часто задаваемые вопросы

### Q: Почему не возвращать `None` вместо исключения?

**A:** Возврат `None` заставляет вызывающий код проверять результат на каждом уровне. Исключения пробрасываются до глобального handler'а, который возвращает корректный HTTP-статус.

### Q: Почему нет try/except в обработчиках шины?

**A:** Ошибки в обработчиках шины должны быть видны в логах с трассировкой. Глобальный обработчик в `main.py` перехватит их и залоггирует.

### Q: Как тестировать код с исключениями?

**A:** Используйте `pytest.raises()`:

```python
async def test_get_profile_not_found():
    with pytest.raises(NotFoundError):
        await service.get_profile(session, uuid.uuid4())
```

### Q: Почему клиенты получают session внутри метода?

**A:** Это упрощает использование — не нужно передавать session вручную. Session создаётся и закрывается автоматически через `get_session()`.

---

## 13. Ссылки

- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 docs](https://docs.sqlalchemy.org/en/20/)
- [Python typing](https://docs.python.org/3/library/typing.html)
- [Pydantic v2](https://docs.pydantic.dev/latest/)
