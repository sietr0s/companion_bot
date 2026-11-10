"""Админский CRUD собеседников Telegram."""

from fastapi import APIRouter

from src.base.routers import create_crud_router
from src.modules.users.dependencies import get_user_service
from src.modules.users.schemas.api import UserCreate, UserRead, UserUpdate

router = APIRouter()

router.include_router(
    create_crud_router(
        get_service=get_user_service,
        create_schema=UserCreate,
        update_schema=UserUpdate,
        response_schema=UserRead,
        prefix="",
        tags=["Users"],
        entity_name="User",
    )
)
