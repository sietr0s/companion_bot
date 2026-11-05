"""Manager access level for all memory entities."""

from src.core.routers import create_manager_router

from .conversations import router as conversations_router
from .messages import router as messages_router
from .summaries import router as summaries_router
from .topics import router as topics_router
from .vectors import router as vectors_router

router = create_manager_router(prefix="/api/v1/public/memory", tags=["Memory"])
router.include_router(conversations_router)
router.include_router(messages_router)
router.include_router(summaries_router)
router.include_router(vectors_router)
router.include_router(topics_router)
