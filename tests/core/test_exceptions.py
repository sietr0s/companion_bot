"""
Тесты исключений приложения.
"""

from src.core.exceptions import (
    AppException,
    ConflictError,
    NotFoundError,
    UnauthorizedError,
)


class TestExceptions:
    """Тесты иерархии исключений."""

    def test_app_exception_defaults(self):
        """Базовое исключение имеет статус 500."""
        exc = AppException()
        assert exc.status_code == 500
        assert exc.detail == "Внутренняя ошибка сервера"

    def test_not_found_error(self):
        exc = NotFoundError()
        assert exc.status_code == 404
        assert isinstance(exc, AppException)

    def test_conflict_error(self):
        exc = ConflictError(detail="Дублирование")
        assert exc.status_code == 409
        assert exc.detail == "Дублирование"

    def test_unauthorized_error(self):
        exc = UnauthorizedError()
        assert exc.status_code == 401
        assert isinstance(exc, AppException)

    def test_custom_detail(self):
        exc = NotFoundError(detail="Пользователь не найден")
        assert exc.detail == "Пользователь не найден"
