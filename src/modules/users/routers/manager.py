"""Админский CRUD собеседников Telegram."""

from src.base.routers import create_crud_router
from src.core.routers import create_manager_router
from src.modules.users.dependencies import get_user_service
from src.modules.users.schemas.api import UserCreate, UserRead, UserUpdate

router = create_manager_router(prefix="/api/v1/public/users", tags=["Users"])

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
