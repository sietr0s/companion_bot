"""Тесты утилиты фильтрации (base/filters.py)."""

import pytest

from src.base.filters import Filter, FilterOperator, apply_filters, parse_filters


class TestParseFilters:
    """Тесты парсинга фильтров формата field+operator+value."""

    def test_single_filter(self):
        result = parse_filters(["email+eq+test@test.com"])
        assert len(result) == 1
        assert result[0].field == "email"
        assert result[0].operator == FilterOperator.EQ
        assert result[0].value == "test@test.com"

    def test_multiple_filters(self):
        result = parse_filters(
            [
                "email+eq+test@test.com",
                "age+gt+18",
            ]
        )
        assert len(result) == 2

    def test_value_with_plus_sign(self):
        result = parse_filters(["email+eq+test+test@test.com"])
        assert result[0].value == "test+test@test.com"

    def test_invalid_filter_skipped(self):
        result = parse_filters(["invalid", "also+invalid"])
        assert len(result) == 0

    def test_invalid_operator_skipped(self):
        result = parse_filters(["email+invalid_op+value"])
        assert len(result) == 0

    def test_empty_list(self):
        result = parse_filters([])
        assert len(result) == 0

    def test_in_operator(self):
        result = parse_filters(["status+in+active,pending"])
        assert result[0].operator == FilterOperator.IN
        assert result[0].value == "active,pending"


class TestApplyFilters:
    """Тесты применения фильтров к SQLAlchemy-запросу."""

    @pytest.fixture
    def model_class(self):
        from src.modules.auth.models import Auth

        return Auth

    def test_eq_filter(self, model_class):
        from sqlalchemy import select

        stmt = select(model_class)
        filters = [Filter(field="email", operator=FilterOperator.EQ, value="test@test.com")]
        result = apply_filters(stmt, model_class, filters)
        assert result is not None

    def test_unknown_field_skipped(self, model_class):
        from sqlalchemy import select

        stmt = select(model_class)
        filters = [Filter(field="nonexistent", operator=FilterOperator.EQ, value="x")]
        result = apply_filters(stmt, model_class, filters)
        # Не падает, просто пропускает
        assert result is not None

    def test_all_operators(self, model_class):
        from sqlalchemy import select

        stmt = select(model_class)
        for op in FilterOperator:
            filters = [Filter(field="email", operator=op, value="test")]
            result = apply_filters(stmt, model_class, filters)
            assert result is not None
