"""
Утилита для фильтрации SQLAlchemy-запросов.

Парсит фильтры формата field+operator+value и применяет
их к SQLAlchemy select-запросу. Вынесена из BaseRepository
для переиспользования и тестируемости.
"""

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel as PydanticModel
from sqlalchemy import Select

from src.core.exceptions import InvalidFilterError


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


def parse_filters(
    raw: list[str],
    allowed_fields: set[str] | frozenset[str] | None = None,
) -> list[Filter]:
    """
    Парсит фильтры формата 'field+operator+value'.

    Разделитель — '+', значение — всё после второго '+'.
    Некорректные строки и запрещённые поля приводят к HTTP 422.
    """
    filters = []
    for item in raw:
        parts = item.split("+", 2)
        if len(parts) != 3 or not all(parts):
            raise InvalidFilterError(detail=f"Некорректный фильтр: {item!r}")

        field, operator, value = parts
        if allowed_fields is not None and field not in allowed_fields:
            raise InvalidFilterError(detail=f"Фильтрация по полю '{field}' запрещена")
        try:
            filters.append(Filter(field=field, operator=operator, value=value))
        except ValueError as exc:
            raise InvalidFilterError(
                detail=f"Некорректный оператор фильтра: {operator!r}"
            ) from exc
    return filters


def _coerce_value(column: Any, raw_value: str) -> Any:
    """Преобразовать строковое значение к Python-типу SQLAlchemy-колонки."""
    try:
        python_type = column.property.columns[0].type.python_type
    except (AttributeError, NotImplementedError):
        return raw_value

    if python_type is str:
        return raw_value
    if python_type is bool:
        normalized = raw_value.lower()
        if normalized in {"true", "1"}:
            return True
        if normalized in {"false", "0"}:
            return False
        raise InvalidFilterError(detail=f"Некорректное boolean-значение: {raw_value!r}")
    if python_type is datetime:
        converter = datetime.fromisoformat
    elif python_type is date:
        converter = date.fromisoformat
    else:
        converter = python_type
    try:
        return converter(raw_value)
    except (TypeError, ValueError) as exc:
        raise InvalidFilterError(
            detail=f"Значение {raw_value!r} не соответствует типу поля"
        ) from exc


def apply_filters(stmt: Select, model: type, filters: list[Filter]) -> Select:
    """
    Применяет список фильтров к SQLAlchemy select-запросу.

    Неизвестные поля модели приводят к HTTP 422.
    Возвращает модифицированный stmt (immutable pattern SQLAlchemy).
    """
    for f in filters:
        if not hasattr(model, f.field):
            raise InvalidFilterError(detail=f"Неизвестное поле фильтра: '{f.field}'")
        col = getattr(model, f.field)
        value = _coerce_value(col, f.value)
        match f.operator:
            case FilterOperator.EQ:
                stmt = stmt.where(col == value)
            case FilterOperator.NE:
                stmt = stmt.where(col != value)
            case FilterOperator.GT:
                stmt = stmt.where(col > value)
            case FilterOperator.GE:
                stmt = stmt.where(col >= value)
            case FilterOperator.LT:
                stmt = stmt.where(col < value)
            case FilterOperator.LE:
                stmt = stmt.where(col <= value)
            case FilterOperator.LIKE:
                stmt = stmt.where(col.like(value))
            case FilterOperator.ILIKE:
                stmt = stmt.where(col.ilike(value))
            case FilterOperator.IN:
                values = [_coerce_value(col, item) for item in f.value.split(",")]
                stmt = stmt.where(col.in_(values))
    return stmt


def apply_ordering(stmt: Select, model: type, order_by: str | None) -> Select:
    """Применить безопасную сортировку: `field` для ASC, `-field` для DESC."""
    if order_by is None:
        return stmt

    descending = order_by.startswith("-")
    field = order_by[1:] if descending else order_by
    if not field or not hasattr(model, field):
        raise InvalidFilterError(detail=f"Неизвестное поле сортировки: '{field}'")

    column = getattr(model, field)
    if not hasattr(column, "asc") or not hasattr(column, "desc"):
        raise InvalidFilterError(detail=f"Поле '{field}' не поддерживает сортировку")
    direction = column.desc if descending else column.asc
    clauses = [direction()]

    # Одинаковые timestamp встречаются часто; ID делает пагинацию стабильной.
    if field != "id" and hasattr(model, "id"):
        id_column = model.id
        clauses.append(id_column.desc() if descending else id_column.asc())

    return stmt.order_by(*clauses)
