"""Manager-level composition for users."""

from fastapi import APIRouter

from src.core.routers import create_manager_router

from .configuration import router as configuration_router
from .users import router as users_router

module_router = APIRouter(prefix="/users")
router = create_manager_router(prefix="/public", tags=["Users"])
module_router.include_router(configuration_router)
module_router.include_router(users_router)

router.include_router(module_router)

__all__ = ["router"]
