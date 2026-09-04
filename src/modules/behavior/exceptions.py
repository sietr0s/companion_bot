"""Behavior module exceptions."""

from src.core.exceptions import AppException


class BehaviorError(AppException):
    detail = "Behavior error"
    status_code = 500
