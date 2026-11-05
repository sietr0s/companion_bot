"""Compose anonymous/self-service and manager authentication routes."""

from fastapi import APIRouter

from .manager import router as manager_router
from .public import router as public_router

router = APIRouter()
router.include_router(public_router)
router.include_router(manager_router)

__all__ = ["router"]
