"""Alembic and monolith model discovery use the explicit module registry."""


def load_models() -> None:
    from src.composition.modules import load_modules

    load_modules()
