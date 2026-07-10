"""Роутеры модуля classifier."""

from src.modules.classifier.routers.internal import router as internal_router
from src.modules.classifier.routers.public import router as public_router

__all__ = ["public_router", "internal_router"]
