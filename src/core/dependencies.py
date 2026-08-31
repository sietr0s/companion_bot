"""
Зависимости FastAPI (Depends).

Централизованное место для внедрения общих зависимостей.
Модули регистрируют свои DI-фабрики в собственных
файлах dependencies.py — ядро не знает о модулях.
"""

import uuid
from collections.abc import AsyncGenerator

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.exceptions import UnauthorizedError
from src.core.security import decode_access_token

# Схема авторизации — извлекает Bearer-токен из заголовка
security_scheme = HTTPBearer()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Провайдер сессии БД для внедрения через Depends.

    Делегирует создание сессии в database.py,
    здесь — только обёртка для DI-контейнера.
    """
    async for session in get_session():
        yield session


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> uuid.UUID:
    """
    Извлечение ID текущего пользователя из JWT.

    Декодирует токен и возвращает UUID из поля sub.
    Используется как зависимость в защищённых эндпоинтах.
    """
    token = credentials.credentials
    payload = decode_access_token(token)
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedError(detail="Токен не содержит идентификатор пользователя")
    try:
        return uuid.UUID(user_id_str)
    except ValueError:
        raise UnauthorizedError(detail="Некорректный идентификатор в токене")


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> uuid.UUID:
    """
    Извлечение ID администратора из JWT.

    Проверяет что role=admin, иначе — Forbidden.
    """
    token = credentials.credentials
    payload = decode_access_token(token)
    user_id_str = payload.get("sub")
    role = payload.get("role", "user")
    if not user_id_str:
        raise UnauthorizedError(detail="Токен не содержит идентификатор пользователя")
    if role != "admin":
        raise UnauthorizedError(detail="Недостаточно прав")
    try:
        return uuid.UUID(user_id_str)
    except ValueError:
        raise UnauthorizedError(detail="Некорректный идентификатор в токене")


# --- Клиенты для межмодульного взаимодействия (прямой вызов без HTTP) ---
# Эти клиенты используются в обработчиках шины (не в HTTP-роутерах).
# Они получают шину сообщений через DI, а не создают новую.


def get_users_client():
    """
    Фабрика клиента пользователей для прямого вызова сервисов.

    Прямой вызов UserService без HTTP.
    """
    from src.core.clients.users_client import UsersClient

    return UsersClient()

