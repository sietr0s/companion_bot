"""Исключения модуля telegram_clients."""

from src.core.exceptions import BadRequestError


class InvalidTelegramCodeError(BadRequestError):
    def __init__(self, detail: str = "Неверный или истёкший код подтверждения"):
        super().__init__(detail=detail)
