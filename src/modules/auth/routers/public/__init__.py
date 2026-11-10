from fastapi import APIRouter

from .sessions import router as sessions_router

module_router = APIRouter(prefix="/auth")
router = APIRouter(prefix="/public")
module_router.include_router(sessions_router)
router.include_router(module_router)

__all__ = ["router"]
