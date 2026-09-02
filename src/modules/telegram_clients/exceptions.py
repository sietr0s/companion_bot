"""Исключения модуля telegram_clients."""

from src.core.exceptions import BadRequestError, NotFoundError


class TelegramAccountNotFoundError(NotFoundError):
    def __init__(self, detail: str = "Telegram-аккаунт не найден"):
        super().__init__(detail=detail)


class InvalidTelegramCodeError(BadRequestError):
    def __init__(self, detail: str = "Неверный или истёкший код подтверждения"):
        super().__init__(detail=detail)
