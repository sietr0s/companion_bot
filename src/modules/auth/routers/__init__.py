"""Роутеры модуля auth."""

from .internal import router as internal_router
from .public import router as public_router

__all__ = ["public_router", "internal_router"]
