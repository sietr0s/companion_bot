"""Manager routes grouped by entity; authentication is applied by the level router."""

from fastapi import APIRouter

from src.base.routers import create_crud_router
from src.modules.instagram_clients.dependencies import (
    get_instagram_chat_state_service,
)
from src.modules.instagram_clients.schemas.api import (
    InstagramChatStateCreate,
    InstagramChatStateRead,
    InstagramChatStateUpdate,
)

router = APIRouter()

router.include_router(
    create_crud_router(
        get_service=get_instagram_chat_state_service,
        create_schema=InstagramChatStateCreate,
        update_schema=InstagramChatStateUpdate,
        response_schema=InstagramChatStateRead,
        prefix="/chat-states",
        tags=["Instagram Chat States"],
        entity_name="InstagramChatState",
    )
)
