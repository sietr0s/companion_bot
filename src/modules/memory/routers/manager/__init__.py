"""Manager access level for all memory entities."""

from fastapi import APIRouter

from src.core.routers import create_manager_router

from .conversations import router as conversations_router
from .messages import router as messages_router
from .summaries import router as summaries_router
from .topics import router as topics_router
from .vectors import router as vectors_router

module_router = APIRouter(prefix="/memory")
router = create_manager_router(prefix="/public", tags=["Memory"])
module_router.include_router(conversations_router)
module_router.include_router(messages_router)
module_router.include_router(summaries_router)
module_router.include_router(vectors_router)
module_router.include_router(topics_router)

router.include_router(module_router)
