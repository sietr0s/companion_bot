"""Monolith entrypoint; module-owned lifecycle and routers live in modules/*/main.py."""

from fastapi import FastAPI

from src.composition.application import create_application
from src.composition.modules import MODULE_NAMES


def create_app(*, modules: tuple[str, ...] = MODULE_NAMES) -> FastAPI:
    return create_application(modules)


app = create_app()
