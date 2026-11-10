"""Compose access-level routers; API version belongs to this module boundary."""

from fastapi import APIRouter

from .manager import router as manager_router

router = APIRouter(prefix="/api/v1")
router.include_router(manager_router)

__all__ = ["router"]
