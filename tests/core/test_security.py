"""
Тесты модуля безопасности: хэширование паролей и JWT.
"""

import uuid

import pytest

from src.core.exceptions import UnauthorizedError
from src.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    """Тесты хэширования и проверки паролей."""

    def test_hash_password_returns_different_hashes(self):
        """Одинаковые пароли дают разные хэши (благодаря соли)."""
        hashed1 = hash_password("mypassword")
        hashed2 = hash_password("mypassword")
        assert hashed1 != hashed2

    def test_verify_password_correct(self):
        """Корректная проверка пароля."""
        hashed = hash_password("mypassword")
        assert verify_password("mypassword", hashed) is True

    def test_verify_password_incorrect(self):
        """Неверный пароль не проходит проверку."""
        hashed = hash_password("mypassword")
        assert verify_password("wrongpassword", hashed) is False


class TestJWT:
    """Тесты создания и декодирования JWT-токенов."""

    def test_create_and_decode_token(self):
        """Токен декодируется и содержит корректный sub."""
        user_id = str(uuid.uuid4())
        token = create_access_token(user_id)
        payload = decode_access_token(token)
        assert payload["sub"] == user_id

    def test_decode_invalid_token(self):
        """Невалидный токен выбрасывает UnauthorizedError."""
        with pytest.raises(UnauthorizedError):
            decode_access_token("invalid.token.here")

    def test_decode_tampered_token(self):
        """Подделанный токен выбрасывает UnauthorizedError."""
        user_id = str(uuid.uuid4())
        token = create_access_token(user_id)
        # Подменяем один символ
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(UnauthorizedError):
            decode_access_token(tampered)
