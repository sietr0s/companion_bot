"""
Базовая схема для пагинированных ответов.

Используется во всех list-эндпоинтах для единообразного ответа.
"""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Универсальный ответ с пагинацией."""

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def from_list(
        cls,
        items: list[T],
        total: int,
        page: int = 1,
        page_size: int = 100,
    ) -> "PaginatedResponse[T]":
        """Создать ответ из списка с вычислением total_pages."""
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=max(1, (total + page_size - 1) // page_size),
        )
