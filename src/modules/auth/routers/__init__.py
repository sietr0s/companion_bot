"""Compose access-level routers; API version belongs to this module boundary."""

from fastapi import APIRouter

from .manager import router as manager_router
from .public import router as public_router

router = APIRouter(prefix="/api/v1")
router.include_router(public_router)
router.include_router(manager_router)

__all__ = ["router"]
