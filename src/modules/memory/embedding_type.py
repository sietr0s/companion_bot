"""Dialect-aware embedding column: pgvector on PostgreSQL, JSON on SQLite."""

from __future__ import annotations

from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, TypeDecorator
from sqlalchemy.engine import Dialect


class EmbeddingVector(TypeDecorator):
    """Store list[float] as vector(dim) on Postgres and JSON on SQLite."""

    impl = JSON
    cache_ok = True
    # Forward pgvector operators (cosine_distance, etc.) used by search_similar.
    comparator_factory = Vector.comparator_factory

    def __init__(self, dim: int) -> None:
        super().__init__()
        self.dim = dim

    def load_dialect_impl(self, dialect: Dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(Vector(self.dim))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value: Any, dialect: Dialect) -> list[float] | None:
        if value is None:
            return None
        return [float(x) for x in value]

    def process_result_value(self, value: Any, dialect: Dialect) -> list[float] | None:
        if value is None:
            return None
        return [float(x) for x in value]
