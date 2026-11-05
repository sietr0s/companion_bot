"""Manager routes grouped by entity; authentication is applied by the level router."""

from fastapi import APIRouter

from src.base.routers import create_crud_router
from src.modules.memory.dependencies import get_message_service
from src.modules.memory.schemas.api import (
    MemoryMessageCreate,
    MemoryMessageRead,
    MemoryMessageUpdate,
)

router = APIRouter()

router.include_router(
    create_crud_router(
        get_service=get_message_service,
        create_schema=MemoryMessageCreate,
        update_schema=MemoryMessageUpdate,
        response_schema=MemoryMessageRead,
        prefix="/messages",
        tags=["Memory"],
        entity_name="Message",
    )
)
