"""Shared access policy for manager HTTP APIs across all modules."""

from enum import Enum

from fastapi import APIRouter, Depends

from src.core.dependencies import get_current_admin


def create_manager_router(*, prefix: str = "", tags: list[str | Enum] | None = None) -> APIRouter:
    return APIRouter(
        prefix=prefix,
        tags=tags,
        dependencies=[Depends(get_current_admin)],
    )
