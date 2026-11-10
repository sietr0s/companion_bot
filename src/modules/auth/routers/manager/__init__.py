"""Manager-level composition for auth."""

from fastapi import APIRouter

from src.core.routers import create_manager_router

from .accounts import router as accounts_router

module_router = APIRouter(prefix="/auth")
router = create_manager_router(prefix="/public", tags=["Auth"])
module_router.include_router(accounts_router)

router.include_router(module_router)

__all__ = ["router"]
