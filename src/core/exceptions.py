"""
Иерархия исключений приложения.

Каждое исключение несёт HTTP-статус, что позволяет
в будущем добавить единый exception handler в FastAPI
для автоматического формирования ответов об ошибках.
"""


class AppException(Exception):  # noqa: N818 — осознанное имя, используется как AppException в handler'ах
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
    """Конфликт — например, дублирование уникального поля (409)."""

    def __init__(self, detail: str = "Конфликт данных"):
        super().__init__(status_code=409, detail=detail)


class UnauthorizedError(AppException):
    """Ошибка авторизации (401)."""

    def __init__(self, detail: str = "Не авторизован"):
        super().__init__(status_code=401, detail=detail)


class InvalidFilterError(AppException):
    """Некорректный или запрещённый фильтр (422)."""

    def __init__(self, detail: str = "Некорректный фильтр"):
        super().__init__(status_code=422, detail=detail)


class ValidationError(AppException):
    """Ошибка валидации данных (422)."""

    def __init__(self, detail: str = "Ошибка валидации"):
        super().__init__(status_code=422, detail=detail)


class BadRequestError(AppException):
    """Некорректный запрос (400)."""

    def __init__(self, detail: str = "Некорректный запрос"):
        super().__init__(status_code=400, detail=detail)
