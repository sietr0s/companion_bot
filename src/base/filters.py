"""
Утилита для фильтрации SQLAlchemy-запросов.

Парсит фильтры формата field+operator+value и применяет
их к SQLAlchemy select-запросу. Вынесена из BaseRepository
для переиспользования и тестируемости.
"""

from enum import StrEnum

from pydantic import BaseModel as PydanticModel
from sqlalchemy import Select


class FilterOperator(StrEnum):
    """Поддерживаемые операторы фильтрации."""

    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GE = "ge"
    LT = "lt"
    LE = "le"
    LIKE = "like"
    ILIKE = "ilike"
    IN = "in"


class Filter(PydanticModel):
    """Один фильтр: field + operator + value."""

    field: str
    operator: FilterOperator
    value: str


def parse_filters(raw: list[str]) -> list[Filter]:
    """
    Парсит фильтры формата 'field+operator+value'.

    Разделитель — '+', значение — всё после второго '+'.
    Некорректные строки silently пропускаются.
    """
    filters = []
    for item in raw:
        parts = item.split("+", 2)
        if len(parts) == 3:
            try:
                filters.append(Filter(field=parts[0], operator=parts[1], value=parts[2]))
            except ValueError:
                continue
    return filters


def apply_filters(stmt: Select, model: type, filters: list[Filter]) -> Select:
    """
    Применяет список фильтров к SQLAlchemy select-запросу.

    Неизвестные поля модели silently пропускаются.
    Возвращает модифицированный stmt (immutable pattern SQLAlchemy).
    """
    for f in filters:
        if not hasattr(model, f.field):
            continue
        col = getattr(model, f.field)
        match f.operator:
            case FilterOperator.EQ:
                stmt = stmt.where(col == f.value)
            case FilterOperator.NE:
                stmt = stmt.where(col != f.value)
            case FilterOperator.GT:
                stmt = stmt.where(col > f.value)
            case FilterOperator.GE:
                stmt = stmt.where(col >= f.value)
            case FilterOperator.LT:
                stmt = stmt.where(col < f.value)
            case FilterOperator.LE:
                stmt = stmt.where(col <= f.value)
            case FilterOperator.LIKE:
                stmt = stmt.where(col.like(f.value))
            case FilterOperator.ILIKE:
                stmt = stmt.where(col.ilike(f.value))
            case FilterOperator.IN:
                stmt = stmt.where(col.in_(f.value.split(",")))
    return stmt
