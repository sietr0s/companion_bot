"""Исключения модуля Example."""

from src.core.exceptions import AppException


class ExampleNotFoundError(AppException):
    """Example не найден (404)."""

    def __init__(self, detail: str = "Example не найден"):
        super().__init__(status_code=404, detail=detail)


class ExampleConflictError(AppException):
    """Конфликт данных Example (409)."""

    def __init__(self, detail: str = "Конфликт данных Example"):
        super().__init__(status_code=409, detail=detail)
