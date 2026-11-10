"""Manager-level composition for batching."""

from fastapi import APIRouter

from src.core.routers import create_manager_router

from .configuration import router as configuration_router

module_router = APIRouter(prefix="/batching")
router = create_manager_router(prefix="/public")

module_router.include_router(configuration_router)
router.include_router(module_router)

__all__ = ["router"]
