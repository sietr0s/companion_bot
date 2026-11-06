"""Manager routes grouped by entity; authentication is applied by the level router."""

from fastapi import APIRouter

from src.base.routers import create_crud_router
from src.modules.memory.dependencies import get_conversation_service
from src.modules.memory.schemas.api import (
    ConversationCreate,
    ConversationRead,
    ConversationUpdate,
)

router = APIRouter()

router.include_router(
    create_crud_router(
        get_service=get_conversation_service,
        create_schema=ConversationCreate,
        update_schema=ConversationUpdate,
        response_schema=ConversationRead,
        prefix="/conversations",
        tags=["Memory"],
        entity_name="Conversation",
    )
)
