"""Админский CRUD собеседников Telegram."""

from fastapi import APIRouter, Depends

from src.base.routers import create_crud_router
from src.core.dependencies import get_current_admin
from src.modules.users.dependencies import get_user_service
from src.modules.users.schemas.public import UserCreate, UserRead, UserUpdate

router = APIRouter(
    prefix="/api/v1/public/users",
    tags=["Users"],
    dependencies=[Depends(get_current_admin)],
)
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
