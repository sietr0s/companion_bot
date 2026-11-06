"""Manager routes grouped by entity; authentication is applied by the level router."""

from fastapi import APIRouter

from src.base.routers import create_crud_router
from src.modules.telegram_clients.dependencies import (
    get_telegram_chat_state_service,
)
from src.modules.telegram_clients.schemas.api import (
    ChatStateCreate,
    ChatStateRead,
    ChatStateUpdate,
)

router = APIRouter()

router.include_router(
    create_crud_router(
        get_service=get_telegram_chat_state_service,
        create_schema=ChatStateCreate,
        update_schema=ChatStateUpdate,
        response_schema=ChatStateRead,
        prefix="/chat-states",
        tags=["Telegram Chat States"],
        entity_name="TelegramChatState",
    )
)
