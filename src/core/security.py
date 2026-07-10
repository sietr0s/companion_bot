"""
Утилиты безопасности: хэширование паролей и работа с JWT.

Разделение на функции без состояния упрощает тестирование
и переиспользование в разных модулях.
"""

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from src.core.config import settings
from src.core.exceptions import UnauthorizedError


def hash_password(password: str) -> str:
    """Хэширование пароля с помощью bcrypt. Автоматическая генерация соли."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Проверка пароля против хэша."""
    return bcrypt.checkpw(
        plain.encode("utf-8"),
        hashed.encode("utf-8"),
    )


def create_access_token(user_id: str, role: str = "user") -> str:
    """
    Создание JWT-токена с временем жизни из настроек.

    sub (subject) — стандартное поле JWT для идентификации пользователя.
    role — роль пользователя (user/admin).
    exp — время истечения токена.
    """
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    """
    Декодирование и валидация JWT-токена.

    При ошибке (истёк, неверная подпись) выбрасывает UnauthorizedError.
    """
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.PyJWTError as e:
        raise UnauthorizedError(detail=f"Недействительный токен: {e}")
